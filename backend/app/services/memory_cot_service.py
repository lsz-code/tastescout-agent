import json
from typing import Any

from app.agent.llm_client import AgentLLMClient
from app.models.favorite_restaurant import FavoriteRestaurant
from app.models.reviews import Review
from app.models.user_memory import UserMemory
from app.schemas.memory import LongTermMemoryData, PricePreference

class MemoryCOTService:
    """
    长期记忆的LLM结构化总结服务

    注意:
    这里不保存，不返回完整的CoT过程，而是只保存最终的总结结果。
    LLM只用于根据收藏和评论生成结构化偏好结论。
    """

    def __init__(self,llm_client: AgentLLMClient | None = None)-> None:
        """
        初始化长期记忆总结服务。

        Args:
            llm_client: 可选的LLM客户端实例，如果不提供，默认使用AgentLLMClient。
        """
        self.llm_client = llm_client or AgentLLMClient()

        async def summarize_memory(
                self,
                favorites:list[FavoriteRestaurant],
                reviews:list[Review],
                baseline_memory:LongTermMemoryData,
                old_memory:UserMemory,
        )-> LongTermMemoryData | None:
            """
            根据用户收藏和评论生成增强版长期记忆。

            逻辑：
            1. 先把收藏、评论、旧记忆和规则版 baseline 组织成 evidence。
            2. 调用 LLM 输出严格 JSON。
            3. 把 JSON 转成 LongTermMemoryData。
            4. 如果 LLM 不可用、调用失败或输出格式不合法，返回 None。

            返回 None 的目的是让上层 MemoryService 自动回退到原来的规则总结结果。
            """
            if not self.llm_client.available:
                return None
            
            evidence = {
                "baseline_memory":baseline_memory.dump(),
                "old_memory":{
                    "avoid_foods":old_memory.avoid_foods or [],
                    "source_version": old_memory.source_version or 0,
                },
                "favorites":[self._favorite_to_dict(fav) for fav in favorites[:30]],
                "reviews":[self._review_to_evidence(item) for item in reviews[:50]],
            }
            
            payload = {
                "model":self.llm_client.model,
                "message":[
                    {
                        "role": "system",
                        "content": (
                            "你是 TasteScout 的长期饮食记忆分析器。"
                            "你需要根据用户收藏餐厅和用户评论，总结用户饮食偏好。"
                            "不要输出思维链，不要输出推理过程，只输出严格 JSON。"
                            "JSON 字段必须包括："
                            "favorite_cuisines, taste_preference, avoid_foods, price_preference, "
                            "favorite_dishes, preferred_scenes, memory_summary。"
                            "price_preference 必须是对象，可包含 min_price, max_price, avg_price。"
                            "所有字段都用中文。"
                        ),
                    },
                    {
                        "role":"user",
                        "content": json.dumps(evidence, ensure_ascii=False),
                    },
                ],
                "temperature":0.2,
                "enable_thinking":False,
            }

            try:
                data = await self.llm_client._chat_completions(payload)
                content = (
                    (data.get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content")
                )
                parsed = self._parse_llm_content(content)
                if not parsed:
                    return None
                return self._build_memory_data(
                    parsed=parsed,
                    baseline_memory=baseline_memory,
                    old_memory=old_memory,
                )
            except Exception:
                return None
    
    def _build_memory_data(
        self,
        parsed: dict[str, Any],
        baseline_memory: LongTermMemoryData,
        old_memory: UserMemory,
    ) -> LongTermMemoryData:
        """
        把 LLM 返回的 JSON 字典转换成 LongTermMemoryData。

        这里会做容错：
        - 如果某个字段缺失，则回退到 baseline_memory。
        - 如果 price_preference 格式不合法，则使用 baseline 的价格偏好。
        - source_version 在旧版本基础上加 1。
        """
        source_version = (old_memory.source_version or 0) + 1

        price_preference = parsed.get("price_preference")
        if not isinstance(price_preference, dict):
            price_preference = baseline_memory.price_preference.model_dump()

        return LongTermMemoryData(
            favorite_cuisines=self._as_str_list(
                parsed.get("favorite_cuisines"),
                fallback=baseline_memory.favorite_cuisines,
            ),
            taste_preference=self._as_str_list(
                parsed.get("taste_preference"),
                fallback=baseline_memory.taste_preference,
            ),
            avoid_foods=self._as_str_list(
                parsed.get("avoid_foods"),
                fallback=baseline_memory.avoid_foods,
            ),
            price_preference=PricePreference(
                min_price=self._to_int(price_preference.get("min_price")),
                max_price=self._to_int(price_preference.get("max_price")),
                avg_price=self._to_float(price_preference.get("avg_price")),
            ),
            favorite_dishes=self._as_str_list(
                parsed.get("favorite_dishes"),
                fallback=baseline_memory.favorite_dishes,
            ),
            preferred_scenes=self._as_str_list(
                parsed.get("preferred_scenes"),
                fallback=baseline_memory.preferred_scenes,
            ),
            memory_summary=self._clean_text(
                parsed.get("memory_summary"),
                fallback=baseline_memory.memory_summary,
            ),
            source_version=source_version,
        )

    @staticmethod
    def _favorite_to_evidence(favorite: FavoriteRestaurant) -> dict[str, Any]:
        """
        把收藏餐厅对象转换成可供 LLM 分析的证据结构。

        只传递和用户偏好有关的字段，避免把无关数据库字段暴露给 LLM。
        """
        return {
            "poi_id": favorite.poi_id,
            "name": favorite.name,
            "address": favorite.address,
            "cuisine_type": favorite.cuisine_type,
            "rating": favorite.rating,
            "avg_price": favorite.avg_price,
            "recommended_dishes": favorite.recommended_dishes,
            "review_summary": favorite.review_summary,
            "recommend_reason": favorite.recommend_reason,
        }
    @staticmethod
    def _review_to_evidence(review: Review) -> dict[str, Any]:
        """
        把用户评论转换成可供 LLM 分析的证据结构。

        评论内容是最重要的偏好信号；
        关联餐厅信息用于帮助 LLM 理解评论对应的菜系、价格和地点。
        """
        restaurant = review.restaurant
        return {
            "content": review.content,
            "rating": review.rating,
            "restaurant": {
                "poi_id": restaurant.poi_id if restaurant else None,
                "name": restaurant.name if restaurant else None,
                "cuisine_type": restaurant.cuisine_type if restaurant else None,
                "avg_price": restaurant.avg_price if restaurant else None,
                "address": restaurant.address if restaurant else None,
            },
        }

    @staticmethod
    def _parse_json_content(content: Any) -> dict[str, Any] | None:
        """
        解析 LLM 返回的 JSON 内容。

        兼容两种情况：
        1. 直接返回 JSON 字符串。
        2. 返回 ```json ... ``` 代码块。

        如果解析失败或结果不是 dict，则返回 None。
        """
        if not isinstance(content, str):
            return None

        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None

        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _as_str_list(value: Any, fallback: list[str] | None = None) -> list[str]:
        """
        把任意输入转换成字符串列表。

        如果输入不是 list，则返回 fallback。
        如果 list 中存在非字符串或空字符串，会被过滤掉。
        """
        if not isinstance(value, list):
            return fallback or []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @staticmethod
    def _clean_text(value: Any, fallback: str | None = None) -> str:
        """
        清洗文本字段。

        如果输入不是字符串或清洗后为空，则返回 fallback。
        """
        if not isinstance(value, str):
            return fallback or ""
        text = value.strip()
        return text or fallback or ""

    @staticmethod
    def _to_int(value: Any) -> int | None:
        """
        把输入转换成 int。

        转换失败时返回 None。
        """
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        """
        把输入转换成 float。

        转换失败时返回 None。
        """
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None