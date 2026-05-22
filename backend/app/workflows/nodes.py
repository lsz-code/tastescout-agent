import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import tool_registry as default_tool_registry
from app.agent.followup_question_builder import FollowupQuestionBuilder
from app.agent.intent_parser import IntentParser
from app.agent.llm_client import AgentLLMClient
from app.agent.slot_checker import SlotChecker
from app.agent.slot_extractor import SlotExtractor
from app.memory.short_term import ShortTermMemory
from app.schemas.memory import LongTermMemoryData
from app.services.memory_service import MemoryService
from app.workflows.agent_state import AgentState


class AgentWorkflowNodes:
    def __init__(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        agent_llm_client: AgentLLMClient | None = None,
        intent_parser: IntentParser | None = None,
        tool_registry: Any = None,
    ) -> None:
        self.db = db
        self.short_term_memory = short_term_memory
        self.memory_service = MemoryService(db)
        self.agent_llm_client = agent_llm_client or AgentLLMClient()
        self.intent_parser = intent_parser or IntentParser()
        self.slot_extractor = SlotExtractor()
        self.slot_checker = SlotChecker()
        self.followup_question_builder = FollowupQuestionBuilder()
        self.tool_registry = tool_registry or default_tool_registry

    #加载长短期记忆，提供给后续节点使用，同时处理记忆加载失败的情况，保证agent的鲁棒性。
    async def load_memory(self, state: AgentState) -> dict[str, Any]:
        missing_error = self._missing_required_field(state)
        if missing_error:
            return {
                "intent": "fallback",
                "short_term_memory": {},
                "long_term_memory": {},
                "memory_used": False,
                "error": missing_error,
            }

        user_id = state.get("user_id")
        session_id = state.get("session_id")

        try:
            short_term_memory = await self.short_term_memory.get(session_id)
            memory_response = await self.memory_service.get_long_term_memory(user_id)
            memory = memory_response.memory or LongTermMemoryData()

            return {
                "short_term_memory": short_term_memory,
                "long_term_memory": memory.model_dump(),
                "memory_used": True,
                "tool_calls": state.get("tool_calls", []),
                "error": None,
            }
        except Exception as exc:
            return {
                "short_term_memory": {},
                "long_term_memory": {},
                "memory_used": False,
                "error": str(exc),
            }
    
    #意图分类
    async def classify_intent(self, state: AgentState) -> dict[str, Any]:
        missing_error = self._missing_required_field(state)
        if missing_error:
            return {
                "intent": "fallback",
                "planned_tool_args": {},
                "error": missing_error,
            }

        if state.get("error"):
            return {"intent": "fallback", "planned_tool_args": {}}

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        message = state.get("message")
        location = state.get("location")
        selected: dict[str, Any] | None = None

        #进行意图解析，首先使用基于规则的解析器快速识别一些明显的意图和槽位，提升效率和准确率。
        # 同时也为后续的LLM解析提供线索和上下文。
        parsed = self.intent_parser.parse(
            message=message,
            user_id=user_id,
            session_id=session_id,
        )
        #如果判断为日常闲聊，就直接进入闲聊流程，不进行工具调用了。
        if parsed and parsed.get("tool_name") == "casual_chat":
            return {
                "intent": "casual_chat",
                "planned_tool_args": {},
            }
        #如果解析出了明确的工具调用意图，就直接使用，避免不必要的LLM调用，提升响应速度。
        if parsed and parsed.get("tool_name") in {
            "add_favorite_by_rank",
            "show_favorites",
            "get_user_memory",
            "refresh_user_memory",
        }:
            tool_name = parsed.get("tool_name") or "fallback"
            arguments = self._ensure_context_arguments(
                tool_name=tool_name,
                arguments=parsed.get("arguments") or {},
                state=state,
            )
            return {
                "intent": tool_name,
                "planned_tool_args": arguments,
            }
        #如果按规则未解析出有用的意图，就调用LLM进行更深入的理解和工具选择，
        # 利用LLM强大的语言理解能力来处理复杂和模糊的输入。
        llm_parsed_context: dict[str, Any] | None = None
        try:
            llm_parsed_context = await self.agent_llm_client.extract_message_context(
                message=message or "",
                short_term_memory=state.get("short_term_memory", {}),
                long_term_memory={
                    **state.get("long_term_memory", {}),
                    "current_location": location,
                    "location_label": state.get("location_label"),
                },
            )
            llm_parsed_context = self._normalize_llm_parsed_context(
                llm_parsed_context
            )
        except Exception:
            llm_parsed_context = None

        llm_intent = (
            llm_parsed_context.get("intent")
            if isinstance(llm_parsed_context, dict)
            else None
        )
        if llm_intent == "casual_chat" and not (
            parsed and parsed.get("tool_name") == "search_restaurants"
        ):
            return {
                "intent": "casual_chat",
                "planned_tool_args": {},
                "llm_parsed_context": llm_parsed_context,
            }
        if llm_intent == "search_restaurants":
            selected = {
                "tool_name": "search_restaurants",
                "arguments": {
                    "user_id": user_id,
                    "session_id": session_id,
                },
            }

        pending_slots = state.get("short_term_memory", {}).get("pending_search_slots")
        if selected is None and isinstance(pending_slots, dict):
            supplied_slots = self.slot_extractor.extract(
                message=message or "",
                short_term_memory=state.get("short_term_memory", {}),
                request_location=location,
            )
            if supplied_slots.get("address") or supplied_slots.get("location"):
                selected = {
                    "tool_name": "search_restaurants",
                    "arguments": {
                        "user_id": user_id,
                        "session_id": session_id,
                    },
                }

        try:
            if selected is None:
                selected = await self.agent_llm_client.select_tool(
                    message=message,
                    user_id=user_id,
                    session_id=session_id,
                    short_term_memory=state.get("short_term_memory", {}),
                    long_term_memory={
                        **state.get("long_term_memory", {}),
                        "current_location": location,
                        "location_label": state.get("location_label"),
                    },
                    tools=self.tool_registry.openai_tool_definitions(),
                )
        except Exception:
            selected = None

        #意图判断兜底
        if selected is None:
            selected = parsed

        if selected is None:
            return {"intent": "fallback", "planned_tool_args": {}}

        tool_name = selected.get("tool_name") or "fallback"
        arguments = selected.get("arguments") or {}
        arguments = self._ensure_context_arguments(tool_name, arguments, state)

        return {
            "intent": tool_name,
            "planned_tool_args": arguments,
            "llm_parsed_context": llm_parsed_context,
        }
    #参数提取
    async def extract_slots(self, state: AgentState) -> dict[str, Any]:
        if state.get("intent") != "search_restaurants":
            return {"search_slots": state.get("search_slots")}

        message = state.get("message") or ""
        short_term_memory = state.get("short_term_memory", {})
        #pending_slots表示假如上一次接收的参数不完整，保留的上一轮已有的参数。
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

        return {"search_slots": merged_slots}

    async def check_slots(self, state: AgentState) -> dict[str, Any]:
        if state.get("intent") != "search_restaurants":
            return {"missing_slots": state.get("missing_slots", [])}

        message = state.get("message") or ""
        if self._is_reroll_intent(message):
            return {"missing_slots": []}

        slots = state.get("search_slots") or {}
        missing_slots = self.slot_checker.check_search_slots(slots)
        return {"missing_slots": missing_slots}

    async def ask_followup(self, state: AgentState) -> dict[str, Any]:
        slots = state.get("search_slots") or {}
        missing_slots = state.get("missing_slots") or []
        reply = self.followup_question_builder.build(missing_slots, slots)

        session_id = state.get("session_id")
        if session_id:
            await self.short_term_memory.update(
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

    async def search_restaurants(self, state: AgentState) -> dict[str, Any]:
        return await self._run_tool(state, "search_restaurants")

    async def add_favorite(self, state: AgentState) -> dict[str, Any]:
        return await self._run_tool(state, "add_favorite_by_rank")

    async def show_favorites(self, state: AgentState) -> dict[str, Any]:
        return await self._run_tool(state, "show_favorites")

    async def get_memory(self, state: AgentState) -> dict[str, Any]:
        return await self._run_tool(state, "get_user_memory")

    async def refresh_memory(self, state: AgentState) -> dict[str, Any]:
        return await self._run_tool(state, "refresh_user_memory")

    async def casual_chat(self, state: AgentState) -> dict[str, Any]:
        reply: str | None = None
        message = state.get("message") or ""
        try:
            reply = await self.agent_llm_client.generate_casual_reply(
                message=message,
                short_term_memory=state.get("short_term_memory", {}),
                long_term_memory=state.get("long_term_memory", {}),
            )
        except Exception:
            reply = None

        if reply is None:
            reply = "哈哈，听起来你已经进入“不知道吃什么但必须吃点什么”的状态了。要不要我顺手帮你看看附近有什么靠谱的？"

        return {
            "intent": "casual_chat",
            "reply": reply,
            "tool_result": None,
            "tool_calls": [],
            "data": {
                "casual_chat": True,
            },
            "memory_used": True,
        }

    async def fallback(self, state: AgentState) -> dict[str, Any]:
        return {
            "intent": "fallback",
            "tool_result": None,
            "data": None,
        }

    async def generate_response(self, state: AgentState) -> dict[str, Any]:
        if state.get("reply"):
            return {"reply": state["reply"]}

        reply: str | None = None
        message = state.get("message")

        if not state.get("error") and message is not None:
            try:
                reply = await self.agent_llm_client.generate_reply(
                    user_message=message,
                    tool_name=state.get("intent"),
                    tool_result=state.get("tool_result"),
                )
            except Exception:
                reply = None

        if reply is None:
            reply = self._template_reply(
                tool_name=state.get("intent"),
                result=state.get("tool_result"),
                error=state.get("error"),
            )

        return {"reply": reply}

    async def _run_tool(
        self,
        state: AgentState,
        tool_name: str,
    ) -> dict[str, Any]:
        missing_error = self._missing_required_field(state)
        if missing_error:
            return {
                "intent": "fallback",
                "tool_result": None,
                "data": None,
                "error": missing_error,
            }

        arguments = self._ensure_context_arguments(
            tool_name=tool_name,
            arguments=state.get("planned_tool_args", {}),
            state=state,
        )
        tool_call = {
            "tool_name": tool_name,
            "arguments": arguments,
            "result": None,
            "success": True,
            "error": None,
        }

        if tool_name == "search_restaurants" and arguments.get("missing_location"):
            result = {"missing_location": True, "restaurants": []}
            tool_call["result"] = result
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": result,
                "data": self._build_data(tool_name, result),
                "error": None,
            }

        if tool_name == "search_restaurants" and arguments.get("missing_search_context"):
            result = {"missing_search_context": True, "restaurants": []}
            tool_call["result"] = result
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": result,
                "data": self._build_data(tool_name, result),
                "error": None,
            }

        try:
            result = await self.tool_registry.execute_tool(
                tool_name=tool_name,
                db=self.db,
                short_term_memory=self.short_term_memory,
                arguments=arguments,
            )
            if tool_name == "search_restaurants" and state.get("session_id"):
                await self.short_term_memory.update(
                    state["session_id"],
                    {
                        "pending_search_slots": None,
                        "missing_slots": [],
                    },
                )
            tool_call["result"] = result
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": result,
                "data": self._build_data(tool_name, result),
                "error": None,
            }
        except Exception as exc:
            tool_call["success"] = False
            tool_call["error"] = str(exc)
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": None,
                "data": None,
                "error": str(exc),
            }

    def _ensure_context_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        state: AgentState,
    ) -> dict[str, Any]:
        normalized = dict(arguments or {})
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        message = state.get("message")
        location = state.get("location")

        if user_id is not None:
            normalized["user_id"] = user_id

        if tool_name in {"search_restaurants", "add_favorite_by_rank"} and session_id is not None:
            normalized["session_id"] = session_id

        if tool_name == "search_restaurants" and message is not None:
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

        if tool_name == "add_favorite_by_rank":
            normalized.setdefault("rank", 1)

        return normalized

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

    @staticmethod
    def _contains_nearby_intent(message: str) -> bool:
        return any(keyword in message for keyword in ["附近", "周边"])

    @staticmethod
    def _missing_required_field(state: AgentState) -> str | None:
        #只有user_id,session_id,message是必需的
        for field in ("user_id", "session_id", "message"):
            if not state.get(field):
                return f"missing required field: {field}"
        return None

    def _build_data(
        self,
        tool_name: str,
        result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if result is None:
            return None

        if tool_name == "search_restaurants":
            data = {"restaurants": result.get("restaurants") or []}
            if result.get("missing_location"):
                data["missing_location"] = True
            if result.get("missing_search_context"):
                data["missing_search_context"] = True
            return data

        if tool_name == "show_favorites":
            return {"favorites": result.get("favorites") or []}

        if tool_name in {"get_user_memory", "refresh_user_memory"}:
            return {"memory": result.get("memory") or result}

        if tool_name == "add_favorite_by_rank":
            return {
                "favorite": result,
                "restaurant": result.get("restaurant"),
            }

        return result

    def _template_reply(
        self,
        tool_name: str | None,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str:
        if error:
            return f"操作失败：{error}"

        result = result or {}

        if tool_name == "search_restaurants":
            if result.get("missing_search_context"):
                return "我可以继续帮你换一批，不过还没找到上一轮的搜索条件。你发个地址，或者点一下“使用我的位置”。"
            if result.get("missing_location"):
                return "我可以帮你找，不过还不知道你想看哪附近。你可以发个地址，或者点一下“使用我的位置”。"
            restaurants = result.get("restaurants") or []
            return (
                f"我先帮你挑了 {len(restaurants)} 家，可以看看有没有顺眼的。"
            )

        if tool_name == "add_favorite_by_rank":
            restaurant = result.get("restaurant") or {}
            rank = result.get("rank")
            name = restaurant.get("name") or "这家餐厅"
            return f"已帮你收藏第 {rank} 家：{name}。"

        if tool_name == "show_favorites":
            return "这是你当前收藏的餐厅。"

        if tool_name == "get_user_memory":
            return "这是我当前记录的你的口味偏好。"

        if tool_name == "refresh_user_memory":
            return "已根据你的收藏刷新长期口味偏好。"

        return "我可以帮你搜索餐厅、收藏推荐结果、查看收藏夹或查看口味偏好。"

    @classmethod
    def _normalize_llm_parsed_context(
        cls,
        context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return None

        normalized: dict[str, Any] = {}
        intent = cls._clean_text(context.get("intent"))
        if intent in {"search_restaurants", "casual_chat", "unknown"}:
            normalized["intent"] = intent
        else:
            normalized["intent"] = "unknown"

        for field in ("address", "city", "keyword", "cuisine", "scene"):
            value = cls._clean_text(context.get(field))
            if value:
                normalized[field] = value

        for field in ("budget", "radius", "limit"):
            value = cls._to_int(context.get(field))
            if value is not None:
                normalized[field] = value

        location = context.get("location")
        if isinstance(location, dict):
            longitude = cls._to_float(location.get("longitude"))
            latitude = cls._to_float(location.get("latitude"))
            if longitude is not None and latitude is not None:
                normalized["location"] = {
                    "longitude": longitude,
                    "latitude": latitude,
                }

        if bool(context.get("is_continue_recommendation")):
            normalized["is_continue_recommendation"] = True

        return normalized

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
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"null", "none", "unknown", "未知", "无"}:
            return None
        return text

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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
