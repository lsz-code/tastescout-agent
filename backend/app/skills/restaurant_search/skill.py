from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.schemas.restaurant import Location as RestaurantLocation
from app.schemas.restaurant import RestaurantSearchFilters, RestaurantSearchRequest
from app.agent.followup_question_builder import FollowupQuestionBuilder
from app.agent.slot_checker import SlotChecker
from app.agent.slot_extractor import SlotExtractor
from app.services.restaurant_search_service import RestaurantSearchService
from app.skills.base import Skill

import re


class RestaurantSearchSkill(Skill):
    name = "search_restaurants"
    description = "按用户位置、地址、店名、关键词和偏好搜索餐厅。菜系不是必填项；没有关键词时默认搜索美食。用户找具体店名时，把店名放入 keyword，不要强制填 cuisine。"
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

    def __init__(self) -> None:
        self.slot_extractor = SlotExtractor()
        self.slot_checker = SlotChecker()
        self.followup_question_builder = FollowupQuestionBuilder()

    async def run(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
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


    #准备执行参数
    def prepare_arguments(
    self,
    arguments: dict[str, Any],
    state: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = super().prepare_arguments(arguments, state)

        session_id = state.get("session_id")
        message = state.get("message")
        location = state.get("location")

        if session_id is not None:
            normalized["session_id"] = session_id

        if message is None:
            return normalized

        normalized.setdefault("keyword", "美食")
        normalized.setdefault("limit", 5)

        if self._is_reroll_intent(message):
            restored = self._restore_last_search_context(
                normalized=normalized,
                short_term_memory=state.get("short_term_memory", {}),
            )
            if not restored:
                normalized["missing_search_context"] = True

        if location is not None:
            normalized["location"] = location
            normalized.pop("address", None)

        self._apply_search_slots(normalized, state.get("search_slots") or {})
        self._normalize_search_arguments(normalized, message)

        return normalized

    #进行槽位抽取，优先级：用户输入 > LLM解析 > 上下文，通过调用agent中的工具函数来进行抽取
    def extract_slots(self, state: dict[str, Any]) -> dict[str, Any]:
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
        llm_slots = self._slots_from_llm_context(
            state.get("llm_parsed_context") or {}
        )
        new_slots = {**llm_slots, **new_slots}
        #将用户输入、LLM解析和上下文中的槽位进行合并，形成最终的搜索参数，
        #并进行一些特例处理，比如地址和位置二选一，缺关键词时默认填美食等
        merged_slots = {**context_slots, **pending_slots, **new_slots}
        if new_slots.get("address") and not new_slots.get("location"):
            merged_slots.pop("location", None)
        if new_slots.get("location"):
            merged_slots.pop("address", None)
        if (
            (
                merged_slots.get("location")
                or merged_slots.get("address")
                or merged_slots.get("city")
            )
            and not merged_slots.get("keyword")
            and not merged_slots.get("cuisine")
        ):
            merged_slots["keyword"] = "美食"

        return {"search_slots": merged_slots}

    def check_slots(self, state: dict[str, Any]) -> dict[str, Any]:
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
    
    #构建参数响应
    def build_data(
    self,
    result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if result is None:
            return None

        data = {"restaurants": result.get("restaurants") or []}

        if result.get("missing_location"):
            data["missing_location"] = True

        if result.get("missing_search_context"):
            data["missing_search_context"] = True

        return data
    
    #构建模版回答
    def build_template_reply(
        self,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str | None:
        if error:
            return f"操作失败：{error}"

        result = result or {}

        if result.get("missing_search_context"):
            return "我可以继续帮你换一批，不过还没找到上一轮的搜索条件。你发个地址，或者点一下“使用我的位置”。"

        if result.get("missing_location"):
            return "我可以帮你找，不过还不知道你想看哪附近。你可以发个地址，或者点一下“使用我的位置”。"

        restaurants = result.get("restaurants") or []
        return f"我先帮你挑了 {len(restaurants)} 家，可以看看有没有顺眼的。"
    
    #应用搜索槽位
    def _apply_search_slots(
        self,
        arguments: dict[str, Any],
        slots: dict[str, Any],
    ) -> None:
        if slots.get("address") and not slots.get("location"):
            arguments.pop("location", None)

        for field in ("address", "location", "city", "keyword", "radius", "limit"):
            value = slots.get(field)
            if value is not None and value != "":
                arguments[field] = value

        filters = arguments.get("filters")
        if not isinstance(filters, dict):
            filters = {}

        if slots.get("cuisine"):
            filters["cuisine"] = slots["cuisine"]
            arguments["keyword"] = slots.get("keyword") or slots["cuisine"]
        if slots.get("budget") is not None:
            filters["max_price"] = slots["budget"]
        if slots.get("scene"):
            filters["scene"] = slots["scene"]

        if filters:
            arguments["filters"] = filters
    
    #对搜索参数进行归一化
    def _normalize_search_arguments(
        self,
        arguments: dict[str, Any],
        message: str,
    ) -> None:
        address = arguments.get("address")
        extracted_address = self._extract_address(message)
        if extracted_address:
            arguments.pop("location", None)
        if arguments.get("location") is None and extracted_address and (not address or len(str(address)) < 6):
            arguments["address"] = extracted_address

        if "北京" in message and not arguments.get("city"):
            arguments["city"] = "北京"

        filters = arguments.get("filters")
        if not isinstance(filters, dict):
            filters = {}

        if "川菜" in message:
            arguments["keyword"] = "川菜"
            filters.setdefault("cuisine", "川菜")

        max_price = self._extract_max_price(message)
        if max_price is not None:
            filters["max_price"] = max_price
            radius = self._to_int(arguments.get("radius"))
            if radius is not None and radius < 500:
                arguments["radius"] = 3000

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

    #存储最后一次搜索的上下文，以便用户说“换一批”时可以继续使用
    def _restore_last_search_context(
        self,
        normalized: dict[str, Any],
        short_term_memory: dict[str, Any],
    ) -> bool:
        context = short_term_memory.get("last_search_context")
        if not isinstance(context, dict):
            return False

        for field in ("address", "location", "keyword", "city", "radius", "limit", "filters"):
            value = context.get(field)
            if value is not None and value != "":
                normalized[field] = value

        return bool(normalized.get("location") or normalized.get("address") or normalized.get("keyword"))
    
    #判断关键词规则是否在用户的上下文中
    @staticmethod
    def _is_reroll_intent(message: str) -> bool:
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
    
    #提取地址
    @staticmethod
    def _extract_address(message: str) -> str | None:
        match = re.search(
            r"(?:我(?:现在|目前|这会儿|刚好)?在|(?:我)?人在|(?:现在|目前|这会儿|刚好)在|位置(?:是|在)?|地址(?:是|在)?|我在|在)"
            r"([^，,。；;]+?)(?:附近|周边)?(?:的|$)",
            message,
        )
        if not match:
            match = re.search(
                r"([^，,。；;]{2,20})(?:这边|这里|当地|有啥好吃|有什么好吃)",
                message,
            )
            if not match:
                return None

        address = match.group(1).strip()
        return address or None
    
    #提取最大人均价格
    @staticmethod
    def _extract_max_price(message: str) -> int | None:
        match = re.search(r"人均\s*(\d+)\s*(?:元)?以内", message)
        if not match:
            return None
        return int(match.group(1))
    
    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    #判断用户是否表达了“附近”或“周边”的意图
    @staticmethod
    def _contains_nearby_intent(message: str) -> bool:
        return any(keyword in message for keyword in ["附近", "周边"])

    @staticmethod
    def _slots_from_llm_context(context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(context, dict):
            return {}
        if context.get("intent") != "search_restaurants":
            return {}

        slots: dict[str, Any] = {}
        for field in ("address", "location", "city", "keyword", "radius", "limit"):
            value = context.get(field)
            if value is not None and value != "":
                slots[field] = value

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
        context_slots: dict[str, Any] = {}

        last_search_context = short_term_memory.get("last_search_context")
        if isinstance(last_search_context, dict):
            for field in ("address", "location", "keyword", "radius", "limit", "city"):
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
