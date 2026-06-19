import json
from typing import Any

from app.agent.llm_client import AgentLLMClient
from app.models.favorite_restaurant import FavoriteRestaurant
from app.models.reviews import Review
from app.models.user_memory import UserMemory
from app.schemas.memory import LongTermMemoryData, PricePreference


class MemoryCOTService:
    """
    长期记忆的 LLM 结构化总结服务。

    这里只保存最终总结结果，不保存或返回推理过程。LLM 不可用或输出异常时返回
    None，让上层自动回退到规则总结。
    """

    def __init__(self, llm_client: AgentLLMClient | None = None) -> None:
        self.llm_client = llm_client or AgentLLMClient()

    async def summarize_user_memory(
        self,
        favorites: list[FavoriteRestaurant],
        reviews: list[Review],
        baseline_memory: LongTermMemoryData,
        old_memory: UserMemory,
    ) -> LongTermMemoryData | None:
        if not self.llm_client.available:
            return None

        evidence = {
            "baseline_memory": baseline_memory.model_dump(),
            "old_memory": {
                "avoid_foods": old_memory.avoid_foods or [],
                "source_version": old_memory.source_version or 0,
            },
            "favorites": [self._favorite_to_evidence(item) for item in favorites[:30]],
            "reviews": [self._review_to_evidence(item) for item in reviews[:50]],
        }

        payload = {
            "model": self.llm_client.models,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 TasteScout 的长期饮食记忆分析器。"
                        "你需要根据用户收藏餐厅和用户评论，总结用户饮食偏好。"
                        "不要输出思维链，不要输出推理过程，只输出严格 JSON。"
                        "JSON 字段必须包括：favorite_cuisines, taste_preference, "
                        "avoid_foods, price_preference, favorite_dishes, "
                        "preferred_scenes, memory_summary。"
                        "price_preference 必须是对象，可包含 min_price, "
                        "max_price, avg_price。所有字段都用中文。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(evidence, ensure_ascii=False),
                },
            ],
            "temperature": 0.2,
            "enable_thinking": False,
        }

        try:
            data = await self.llm_client._chat_completions(payload)
            content = (
                (data.get("choices") or [{}])[0]
                .get("message", {})
                .get("content")
            )
            parsed = self._parse_json_content(content)
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
        if not isinstance(content, str):
            return None

        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _as_str_list(value: Any, fallback: list[str] | None = None) -> list[str]:
        if not isinstance(value, list):
            return fallback or []
        return [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]

    @staticmethod
    def _clean_text(value: Any, fallback: str | None = None) -> str:
        if not isinstance(value, str):
            return fallback or ""
        text = value.strip()
        return text or fallback or ""

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
