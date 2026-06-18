import json
from typing import Any

from app.agent.llm_client import AgentLLMClient


class LLMSlotPlanner:
    """使用 LLM 做餐厅搜索槽位补全和追问规划。

    这里不让 LLM 输出思维链，只允许它返回结构化 JSON。
    Workflow 会用这些结构化结果决定是否继续搜索、是否追问用户。
    """

    def __init__(self, llm_client: AgentLLMClient | None = None) -> None:
        """初始化 LLM 槽位规划器。"""
        self.llm_client = llm_client or AgentLLMClient()

    async def plan_search_slots(
        self,
        message: str,
        rule_slots: dict[str, Any],
        short_term_memory: dict[str, Any],
        long_term_memory: dict[str, Any],
        request_location: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """根据用户消息、规则槽位和记忆上下文生成结构化槽位计划。"""
        if not self.llm_client.available:
            return None

        payload = {
            "model": self.llm_client.models,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 TasteScout 的餐厅搜索槽位规划器。"
                        "你只能输出严格 JSON，不要输出解释、Markdown 或推理过程。"
                        "JSON 字段必须包含：intent, slots, missing_slots, "
                        "should_ask_followup, followup_question, assumptions。"
                        "intent 只能是 search_restaurants 或 unknown。"
                        "slots 可包含 address, location, keyword, cuisine, budget, "
                        "scene, radius, limit。"
                        "missing_slots 只能包含 location, cuisine。"
                        "如果用户说随便推荐，并且已有 location 或 address，"
                        "可以把 keyword 设置为 美食，不必追问 cuisine。"
                        "如果用户说附近/周边，但没有 location/address，需要追问 location。"
                        "followup_question 必须是中文。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "message": message,
                            "rule_slots": rule_slots,
                            "request_location": request_location,
                            "short_term_memory": {
                                "pending_search_slots": short_term_memory.get(
                                    "pending_search_slots"
                                ),
                                "last_search_context": short_term_memory.get(
                                    "last_search_context"
                                ),
                                "current_location": short_term_memory.get(
                                    "current_location"
                                ),
                            },
                            "long_term_memory": long_term_memory,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.1,
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
            return self._normalize_plan(parsed)
        except Exception:
            return None

    def _normalize_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        """清洗 LLM 返回的槽位计划，防止异常字段污染 Workflow。"""
        intent = plan.get("intent")
        if intent not in {"search_restaurants", "unknown"}:
            intent = "unknown"

        slots = plan.get("slots")
        if not isinstance(slots, dict):
            slots = {}

        normalized_slots: dict[str, Any] = {}
        for field in (
            "address",
            "location",
            "keyword",
            "cuisine",
            "budget",
            "scene",
            "radius",
            "limit",
        ):
            value = slots.get(field)
            if value is not None and value != "":
                normalized_slots[field] = value

        self._normalize_location_slot(normalized_slots)
        self._normalize_integer_slots(normalized_slots)

        missing_slots = plan.get("missing_slots")
        if not isinstance(missing_slots, list):
            missing_slots = []
        missing_slots = [
            item for item in missing_slots if item in {"location", "cuisine"}
        ]

        followup_question = plan.get("followup_question")
        if isinstance(followup_question, str) and followup_question.strip():
            followup_question = followup_question.strip()
        else:
            followup_question = None

        assumptions = plan.get("assumptions")
        if not isinstance(assumptions, list):
            assumptions = []
        assumptions = [
            item.strip()
            for item in assumptions
            if isinstance(item, str) and item.strip()
        ]

        return {
            "intent": intent,
            "slots": normalized_slots,
            "missing_slots": missing_slots,
            "should_ask_followup": bool(plan.get("should_ask_followup")),
            "followup_question": followup_question,
            "assumptions": assumptions,
        }

    def _normalize_location_slot(self, slots: dict[str, Any]) -> None:
        """规范化 location 字段，只保留 longitude/latitude。"""
        location = slots.get("location")
        if not isinstance(location, dict):
            slots.pop("location", None)
            return

        longitude = self._to_float(location.get("longitude") or location.get("lng"))
        latitude = self._to_float(location.get("latitude") or location.get("lat"))
        if longitude is not None and latitude is not None:
            slots["location"] = {
                "longitude": longitude,
                "latitude": latitude,
            }
        else:
            slots.pop("location", None)

    def _normalize_integer_slots(self, slots: dict[str, Any]) -> None:
        """规范化 budget/radius/limit 这些整数槽位。"""
        for field in ("budget", "radius", "limit"):
            if field not in slots:
                continue
            value = self._to_int(slots[field])
            if value is None:
                slots.pop(field, None)
            else:
                slots[field] = value

    @staticmethod
    def _parse_json_content(content: Any) -> dict[str, Any] | None:
        """解析 LLM 返回的 JSON，兼容 ```json 代码块。"""
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
    def _to_int(value: Any) -> int | None:
        """把输入转换成 int，失败返回 None。"""
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        """把输入转换成 float，失败返回 None。"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
