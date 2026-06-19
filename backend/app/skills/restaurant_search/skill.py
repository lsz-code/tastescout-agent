from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.followup_question_builder import FollowupQuestionBuilder
from app.agent.slot_checker import SlotChecker
from app.agent.slot_extractor import SlotExtractor
from app.memory.short_term import ShortTermMemory
from app.schemas.restaurant import Location as RestaurantLocation
from app.schemas.restaurant import RestaurantSearchFilters, RestaurantSearchRequest
from app.services.restaurant_search_service import RestaurantSearchService
from app.skills.base import Skill


class RestaurantSearchSkill(Skill):
    """餐厅搜索 Skill，负责把 Agent 槽位转换成搜索服务参数。"""

    name = "search_restaurants"
    description = (
        "按用户位置、地址、店名、菜品关键词、菜系和偏好搜索餐厅。"
        "用户找具体店名或菜品时，把名称放入 keyword；菜系只作为过滤条件。"
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "session_id": {"type": "string"},
            "address": {"type": "string"},
            "location": {
                "type": "object",
                "properties": {
                    "longitude": {"type": "number"},
                    "latitude": {"type": "number"},
                },
            },
            "city": {"type": "string"},
            "keyword": {"type": "string"},
            "radius": {"type": "integer", "default": 3000},
            "limit": {"type": "integer", "default": 5},
            "filters": {"type": "object"},
        },
        "required": ["user_id", "session_id"],
    }

    GENERIC_KEYWORDS = {"", "美食", "餐厅", "饭店", "吃饭", "吃的", "好吃的", "随便推荐"}
    CUISINES = {
        "川菜",
        "火锅",
        "烧烤",
        "日料",
        "粤菜",
        "广东菜",
        "潮汕菜",
        "湘菜",
        "东北菜",
        "韩餐",
        "西餐",
        "面馆",
        "小吃",
        "奶茶",
        "甜品",
    }

    def __init__(self) -> None:
        """初始化搜索 Skill 需要的规则抽取器和追问构造器。"""
        self.slot_extractor = SlotExtractor()
        self.slot_checker = SlotChecker()
        self.followup_question_builder = FollowupQuestionBuilder()

    async def run(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """构造 RestaurantSearchRequest 并调用搜索服务。"""
        filters = arguments.get("filters")
        payload = RestaurantSearchRequest(
            user_id=arguments["user_id"],
            session_id=arguments["session_id"],
            address=arguments.get("address"),
            location=(
                RestaurantLocation(**arguments["location"])
                if isinstance(arguments.get("location"), dict)
                else None
            ),
            city=arguments.get("city"),
            keyword=arguments.get("keyword") or "美食",
            radius=arguments.get("radius") or 3000,
            limit=arguments.get("limit") or 5,
            filters=RestaurantSearchFilters(**filters)
            if isinstance(filters, dict)
            else None,
        )

        service = RestaurantSearchService(db=db, short_term_memory=short_term_memory)
        response = await service.search(payload)
        return response.model_dump(mode="json")

    def prepare_arguments(
        self,
        arguments: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """准备搜索工具参数，确保店名/菜品关键词不会被菜系覆盖。"""
        normalized = super().prepare_arguments(arguments, state)
        session_id = state.get("session_id")
        message = state.get("message") or ""
        request_location = state.get("location")

        if session_id is not None:
            normalized["session_id"] = session_id

        normalized.setdefault("limit", 5)
        normalized.setdefault("radius", 3000)

        if self._is_reroll_intent(message):
            restored = self._restore_last_search_context(
                normalized=normalized,
                short_term_memory=state.get("short_term_memory", {}),
            )
            if not restored:
                normalized["missing_search_context"] = True

        if request_location is not None:
            normalized["location"] = request_location
            normalized.pop("address", None)

        self._apply_search_slots(normalized, state.get("search_slots") or {})
        self._normalize_search_arguments(normalized, message)

        if normalized.get("location") is not None:
            normalized.pop("address", None)

        if normalized.get("location") or normalized.get("address") or normalized.get("city"):
            normalized.pop("missing_location", None)

        if not normalized.get("keyword"):
            normalized["keyword"] = "美食"

        normalized["keyword"] = str(normalized["keyword"]).strip() or "美食"
        normalized["search_query"] = normalized.get("search_query") or normalized["keyword"]
        normalized["search_type"] = normalized.get("search_type") or self._infer_search_type(
            normalized["keyword"],
            normalized.get("filters"),
        )
        return normalized

    def extract_slots(self, state: dict[str, Any]) -> dict[str, Any]:
        """抽取并合并搜索槽位，优先使用用户本轮明确输入。"""
        message = state.get("message") or ""
        short_term_memory = state.get("short_term_memory", {})
        pending_slots = short_term_memory.get("pending_search_slots")
        if not isinstance(pending_slots, dict):
            pending_slots = {}

        context_slots = self._build_context_search_slots(
            short_term_memory=short_term_memory,
            request_location=state.get("location"),
        )
        new_slots = self.slot_extractor.extract(
            message=message,
            short_term_memory=short_term_memory,
            request_location=None,
        )
        llm_slots = self._slots_from_llm_context(state.get("llm_parsed_context") or {})

        # 优先级：历史上下文 < 上轮追问槽位 < LLM 当前解析 < 本轮规则解析。
        new_slots = {**llm_slots, **new_slots}
        merged_slots = {**context_slots, **pending_slots, **new_slots}

        if new_slots.get("address") and not new_slots.get("location"):
            merged_slots.pop("location", None)
        if new_slots.get("location"):
            merged_slots.pop("address", None)

        if (
            (merged_slots.get("location") or merged_slots.get("address") or merged_slots.get("city"))
            and not merged_slots.get("keyword")
            and not merged_slots.get("cuisine")
        ):
            merged_slots["keyword"] = "美食"
            merged_slots["search_query"] = "美食"
            merged_slots["search_type"] = "generic"

        return {"search_slots": merged_slots}

    def check_slots(self, state: dict[str, Any]) -> dict[str, Any]:
        """检查搜索必需位置信息，换一批场景复用上次搜索上下文。"""
        message = state.get("message") or ""
        if self._is_reroll_intent(message):
            return {"missing_slots": []}

        slots = state.get("search_slots") or {}
        missing_slots = self.slot_checker.check_search_slots(slots)
        return {"missing_slots": missing_slots}

    async def ask_followup(
        self,
        state: dict[str, Any],
        short_term_memory: ShortTermMemory,
    ) -> dict[str, Any]:
        """生成追问，并把已有关键词、店名或菜系保存在 pending_search_slots。"""
        slots = state.get("search_slots") or {}
        missing_slots = state.get("missing_slots") or []
        reply = self.followup_question_builder.build(missing_slots, slots)

        session_id = state.get("session_id")
        if session_id:
            await short_term_memory.update(
                session_id,
                {
                    "pending_search_slots": slots,
                    "missing_slots": missing_slots,
                    "last_intent": "ask_followup",
                },
            )

        return {
            "reply": reply,
            "data": {
                "needs_followup": True,
                "missing_slots": missing_slots,
                "partial_slots": slots,
            },
        }

    def build_data(self, result: dict[str, Any] | None) -> dict[str, Any] | None:
        """构造前端需要的搜索 data。"""
        if result is None:
            return None

        data = {"restaurants": result.get("restaurants") or []}
        if result.get("missing_location"):
            data["missing_location"] = True
        if result.get("missing_search_context"):
            data["missing_search_context"] = True
        return data

    def build_template_reply(
        self,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str | None:
        """LLM 不可用时的搜索模板回复。"""
        if error:
            return f"操作失败：{error}"

        result = result or {}
        if result.get("missing_search_context"):
            return "我可以继续帮你换一批，不过还没有上一轮搜索条件。你可以发个地址，或者点击“使用我的位置”。"
        if result.get("missing_location"):
            return "我可以帮你找，不过还不知道你想看哪附近。你可以发个地址，或者点击“使用我的位置”。"

        restaurants = result.get("restaurants") or []
        if not restaurants:
            return "暂时没有找到匹配的餐厅，可以换个关键词、补充更具体的位置，或者扩大搜索范围。"
        return f"我先帮你挑了 {len(restaurants)} 家，可以看看有没有顺眼的。"

    def _apply_search_slots(
        self,
        arguments: dict[str, Any],
        slots: dict[str, Any],
    ) -> None:
        """把搜索槽位写入工具执行参数，店名/菜品 keyword 优先于 cuisine。"""
        if slots.get("address") and not slots.get("location"):
            arguments.pop("location", None)

        for field in (
            "address",
            "location",
            "city",
            "keyword",
            "radius",
            "limit",
            "search_query",
            "search_type",
        ):
            value = slots.get(field)
            if value is not None and value != "":
                arguments[field] = value

        filters = arguments.get("filters")
        if not isinstance(filters, dict):
            filters = {}

        if slots.get("cuisine"):
            filters["cuisine"] = slots["cuisine"]
            current_keyword = str(arguments.get("keyword") or "").strip()
            if self._is_generic_keyword(current_keyword):
                arguments["keyword"] = slots["cuisine"]
                arguments["search_query"] = slots["cuisine"]
                arguments["search_type"] = "cuisine"

        if slots.get("budget") is not None:
            filters["max_price"] = slots["budget"]
        if slots.get("scene"):
            filters["scene"] = slots["scene"]

        if filters:
            arguments["filters"] = filters

    def _normalize_search_arguments(
        self,
        arguments: dict[str, Any],
        message: str,
    ) -> None:
        """根据用户原文补齐地址、城市、半径和关键词等搜索参数。"""
        extracted_address = self._extract_address(message)
        if extracted_address and arguments.get("location") is None:
            arguments["address"] = extracted_address

        extracted_keyword = self._extract_keyword_from_message(message)
        if extracted_keyword:
            current_keyword = str(arguments.get("keyword") or "").strip()
            if self._is_generic_keyword(current_keyword) or extracted_keyword not in self.CUISINES:
                arguments["keyword"] = extracted_keyword
                arguments["search_query"] = extracted_keyword
                arguments["search_type"] = "keyword"

        city = self._extract_city(message)
        if city and not arguments.get("city"):
            arguments["city"] = city

        radius = self._extract_radius(message)
        if radius is not None:
            arguments["radius"] = radius

        filters = arguments.get("filters")
        if not isinstance(filters, dict):
            filters = {}

        cuisine = self._extract_cuisine(message)
        if cuisine:
            filters.setdefault("cuisine", cuisine)
            if self._is_generic_keyword(str(arguments.get("keyword") or "")):
                arguments["keyword"] = cuisine
                arguments["search_query"] = cuisine
                arguments["search_type"] = "cuisine"

        max_price = self._extract_max_price(message)
        if max_price is not None:
            filters["max_price"] = max_price

        if filters:
            arguments["filters"] = filters

        if (
            arguments.get("location") is None
            and not arguments.get("address")
            and not arguments.get("city")
            and self._contains_nearby_intent(message)
            and not arguments.get("missing_search_context")
        ):
            arguments["missing_location"] = True

    def _restore_last_search_context(
        self,
        normalized: dict[str, Any],
        short_term_memory: dict[str, Any],
    ) -> bool:
        """从短期记忆恢复上一次搜索条件，用于“换一批”。"""
        context = short_term_memory.get("last_search_context")
        if not isinstance(context, dict):
            return False

        for field in (
            "address",
            "location",
            "keyword",
            "search_query",
            "search_type",
            "city",
            "radius",
            "limit",
            "filters",
        ):
            value = context.get(field)
            if value is not None and value != "":
                normalized[field] = value

        return bool(
            normalized.get("location")
            or normalized.get("address")
            or normalized.get("city")
            or normalized.get("keyword")
        )

    @classmethod
    def _slots_from_llm_context(cls, context: dict[str, Any]) -> dict[str, Any]:
        """从 LLM 意图解析结果中提取搜索槽位。"""
        if not isinstance(context, dict) or context.get("intent") != "search_restaurants":
            return {}

        slots: dict[str, Any] = {}
        for field in ("address", "location", "city", "keyword", "radius", "limit"):
            value = context.get(field)
            if value is not None and value != "":
                slots[field] = value

        if context.get("keyword"):
            slots["search_query"] = context["keyword"]
            slots["search_type"] = "keyword"
        if context.get("cuisine"):
            slots["cuisine"] = context["cuisine"]
        if context.get("budget") is not None:
            slots["budget"] = context["budget"]
        if context.get("scene"):
            slots["scene"] = context["scene"]
        if context.get("is_continue_recommendation"):
            slots["is_continue_recommendation"] = True

        return slots

    @staticmethod
    def _build_context_search_slots(
        short_term_memory: dict[str, Any],
        request_location: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """从短期记忆恢复可复用的搜索上下文槽位。"""
        context_slots: dict[str, Any] = {}

        last_search_context = short_term_memory.get("last_search_context")
        if isinstance(last_search_context, dict):
            for field in (
                "address",
                "location",
                "keyword",
                "search_query",
                "search_type",
                "radius",
                "limit",
                "city",
            ):
                value = last_search_context.get(field)
                if value is not None and value != "":
                    context_slots[field] = value

            filters = last_search_context.get("filters")
            if isinstance(filters, dict):
                if filters.get("cuisine"):
                    context_slots["cuisine"] = filters["cuisine"]
                if filters.get("max_price") is not None:
                    context_slots["budget"] = filters["max_price"]
                if filters.get("scene"):
                    context_slots["scene"] = filters["scene"]

        current_keyword = short_term_memory.get("current_search_keyword")
        if current_keyword:
            context_slots.setdefault("keyword", current_keyword)
            context_slots.setdefault("search_query", current_keyword)

        current_address = short_term_memory.get("current_address")
        if current_address:
            context_slots["address"] = current_address
            context_slots.pop("location", None)

        current_location = short_term_memory.get("current_location")
        if isinstance(current_location, dict):
            context_slots["location"] = current_location

        if request_location:
            context_slots["location"] = request_location
            context_slots.pop("address", None)

        return context_slots

    @staticmethod
    def _is_reroll_intent(message: str) -> bool:
        """判断用户是否表达了“换一批/再推荐”的意图。"""
        return any(
            keyword in message
            for keyword in [
                "再推荐几家",
                "换几家",
                "还有别的吗",
                "还有别的么",
                "还有其他的吗",
                "有没有其他的",
                "不想吃这些",
                "再来几个",
                "再推荐一些别的",
                "重新推荐",
                "换一批",
            ]
        )

    @classmethod
    def _extract_keyword_from_message(cls, message: str) -> str | None:
        """复用 SlotExtractor 的关键词抽取能力。"""
        return SlotExtractor._extract_search_keyword(message)

    @staticmethod
    def _extract_address(message: str) -> str | None:
        """复用 SlotExtractor 的地址抽取能力。"""
        return SlotExtractor._extract_address(message)

    @staticmethod
    def _extract_city(message: str) -> str | None:
        """提取城市名。"""
        return SlotExtractor._extract_city(message)

    @staticmethod
    def _extract_radius(message: str) -> int | None:
        """提取搜索半径。"""
        return SlotExtractor._extract_radius(message)

    @staticmethod
    def _extract_max_price(message: str) -> int | None:
        """提取人均预算上限。"""
        return SlotExtractor._extract_budget(message)

    @classmethod
    def _extract_cuisine(cls, message: str) -> str | None:
        """提取菜系。"""
        for cuisine in cls.CUISINES:
            if cuisine in message:
                return cuisine
        return None

    @classmethod
    def _is_generic_keyword(cls, keyword: str) -> bool:
        """判断 keyword 是否只是泛化搜索词。"""
        return keyword.strip() in cls.GENERIC_KEYWORDS

    @staticmethod
    def _contains_nearby_intent(message: str) -> bool:
        """判断用户是否表达附近/周边意图。"""
        return any(keyword in message for keyword in ["附近", "周边", "周围"])

    @classmethod
    def _infer_search_type(
        cls,
        keyword: str,
        filters: dict[str, Any] | None,
    ) -> str:
        """根据 keyword 和 filters 推断搜索类型。"""
        if cls._is_generic_keyword(keyword):
            return "generic"
        if keyword in cls.CUISINES or (isinstance(filters, dict) and filters.get("cuisine") == keyword):
            return "cuisine"
        return "keyword"
