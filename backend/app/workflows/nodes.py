from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import tool_registry as default_tool_registry
from app.agent.intent_parser import IntentParser
from app.agent.llm_client import AgentLLMClient
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
            arguments = self.tool_registry.prepare_arguments(
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
            supplied_slots = self.tool_registry.extract_slots(
                "search_restaurants",
                {
                    **state,
                    "message": message or "",
                    "location": location,
                },
            ).get("search_slots") or {}
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
        arguments = self.tool_registry.prepare_arguments(tool_name, arguments,state)

        return {
            "intent": tool_name,
            "planned_tool_args": arguments,
            "llm_parsed_context": llm_parsed_context,
        }
    
    #按槽位提取参数
    async def extract_slots(self, state: AgentState) -> dict[str, Any]:
        if state.get("intent") != "search_restaurants":
            return {"search_slots": state.get("search_slots")}

        return self.tool_registry.extract_slots("search_restaurants", state)

    #检查参数完整性，判断是否需要进行补问
    async def check_slots(self, state: AgentState) -> dict[str, Any]:
        if state.get("intent") != "search_restaurants":
            return {"missing_slots": state.get("missing_slots", [])}

        return self.tool_registry.check_slots("search_restaurants", state)

    #进行多轮追问，然后将用户的回答整合到参数中，直到参数完整或者用户放弃。
    async def ask_followup(self, state: AgentState) -> dict[str, Any]:
        return await self.tool_registry.ask_followup(
            "search_restaurants",
            state,
            self.short_term_memory,
        )

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
            reply = self.tool_registry.build_template_reply(
                tool_name=state.get("intent"),
                result=state.get("tool_result"),
                error=state.get("error"),
            )
        
        if reply is None:
            reply = "我可以帮你搜索餐厅、收藏推荐结果、查看收藏夹或查看口味偏好。"

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

        arguments = self.tool_registry.prepare_arguments(
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
                "data": self.tool_registry.build_data(tool_name, result),
                "error": None,
            }

        if tool_name == "search_restaurants" and arguments.get("missing_search_context"):
            result = {"missing_search_context": True, "restaurants": []}
            tool_call["result"] = result
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": result,
                "data": self.tool_registry.build_data(tool_name, result),
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
                "data": self.tool_registry.build_data(tool_name, result),
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

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _missing_required_field(state: AgentState) -> str | None:
        #只有user_id,session_id,message是必需的
        for field in ("user_id", "session_id", "message"):
            if not state.get(field):
                return f"missing required field: {field}"
        return None

    #对LLM解析的结果进行清洗和归一化，提取有用的信息，同时过滤掉无效和不可靠的内容，提升后续处理的准确性和鲁棒性。
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
