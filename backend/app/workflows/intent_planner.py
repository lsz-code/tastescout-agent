from typing import Any

from app.agent.intent_parser import IntentParser
from app.agent.llm_client import AgentLLMClient
from app.workflows.agent_state import AgentState
from app.workflows.state_utils import clean_text, missing_required_field, to_float, to_int


DIRECT_RULE_TOOLS = {
    "add_favorite_by_rank",
    "show_favorites",
    "get_user_memory",
    "refresh_user_memory",
}


class IntentPlanner:
    """负责把用户消息转换成下一步要执行的业务意图和工具参数。"""

    def __init__(
        self,
        agent_llm_client: AgentLLMClient,
        intent_parser: IntentParser,
        tool_registry: Any,
    ) -> None:
        """保存规则解析器、LLM 客户端和 Skill Registry 代理。"""
        self.agent_llm_client = agent_llm_client
        self.intent_parser = intent_parser
        self.tool_registry = tool_registry

    async def plan(self, state: AgentState) -> dict[str, Any]:
        """按“规则优先、LLM 补充、规则兜底”的顺序规划意图。"""
        missing_error = missing_required_field(state)
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
        message = state.get("message") or ""
        location = state.get("location")

        parsed = self.intent_parser.parse(
            message=message,
            user_id=user_id,
            session_id=session_id,
        )

        #规则关键词优先，如果规则解析已经足够明确，就直接执行，避免不必要的 LLM 调用，
        #提升效率和稳定性。只有当规则解析无法明确意图时，才调用 LLM 做进一步分析和判断。
        direct_result = self._try_rule_direct_intent(parsed, state)
        if direct_result is not None:
            return direct_result

        #规则化无法识别，或者识别到的工具需要进一步补齐参数，就调用 LLM 做上下文解析和意图判断，提升理解能力和灵活性。
        llm_parsed_context = await self._extract_llm_context(state)
        selected = self._select_from_llm_context(
            llm_parsed_context=llm_parsed_context,
            parsed=parsed,
            user_id=user_id,
            session_id=session_id,
        )

        #如果LLM也无法解析出意图，就直接使用上一轮规则解析的结果（可能是 None），
        #让后续节点来处理，保证流程的鲁棒性。
        if selected is None:
            selected = self._select_from_pending_slots(
                state=state,
                message=message,
                location=location,
                user_id=user_id,
                session_id=session_id,
            )

        #如果用户在补齐搜索工具的槽位，就直接继续搜索，不需要再经过一次 LLM 选择，提升效率和用户体验。
        if selected is None:
            selected = await self._select_by_llm_tool_call(state)

        #如果LLM 选择工具也失败了，就退回到规则解析的结果（可能是 None），最终兜底到 fallback 节点，保证流程的鲁棒性和可解释性。
        #用户可以通过查看 llm_parsed_context 来理解 LLM 的分析结果，或者通过查看 parsed 来理解规则解析的结果。
        if selected is None:
            selected = parsed

        #如果所有方法都没有选出明确的工具，就进入 fallback，保证流程的鲁棒性。
        if selected is None:
            return {
                "intent": "fallback",
                "planned_tool_args": {},
                "llm_parsed_context": llm_parsed_context,
            }

        #如果选出了明确的工具，就提取工具参数，准备执行。工具参数的准备可能涉及一些通用的衍生计算，
        tool_name = selected.get("tool_name") or "fallback"
        arguments = self.tool_registry.prepare_arguments(
            tool_name=tool_name,
            arguments=selected.get("arguments") or {},
            state=state,
        )

        #最终更新state 的 intent 字段为工具名，planned_tool_args 字段为准备好的参数，
        # llm_parsed_context 字段为 LLM 解析结果（可能是 None），供后续节点使用。
        return {
            "intent": tool_name,
            "planned_tool_args": arguments,
            "llm_parsed_context": llm_parsed_context,
        }

    def _try_rule_direct_intent(
        self,
        parsed: dict[str, Any] | None,
        state: AgentState,
    ) -> dict[str, Any] | None:
        """处理规则解析已经足够明确的意图，减少不必要的 LLM 调用。"""
        if not parsed:
            return None

        tool_name = parsed.get("tool_name")
        if tool_name == "casual_chat":
            return {"intent": "casual_chat", "planned_tool_args": {}}

        if tool_name in DIRECT_RULE_TOOLS:
            arguments = self.tool_registry.prepare_arguments(
                tool_name=tool_name,
                arguments=parsed.get("arguments") or {},
                state=state,
            )
            return {"intent": tool_name, "planned_tool_args": arguments}

        return None

    async def _extract_llm_context(
        self,
        state: AgentState,
    ) -> dict[str, Any] | None:
        """调用 LLM 做轻量结构化解析，失败时返回 None。"""
        try:
            context = await self.agent_llm_client.extract_message_context(
                message=state.get("message") or "",
                short_term_memory=state.get("short_term_memory", {}),
                long_term_memory={
                    **state.get("long_term_memory", {}),
                    "current_location": state.get("location"),
                    "location_label": state.get("location_label"),
                },
            )
            return self._normalize_llm_parsed_context(context)
        except Exception:
            return None

    @staticmethod
    def _select_from_llm_context(
        llm_parsed_context: dict[str, Any] | None,
        parsed: dict[str, Any] | None,
        user_id: str | None,
        session_id: str | None,
    ) -> dict[str, Any] | None:
        """根据 LLM 结构化解析结果直接选出高置信意图。"""
        llm_intent = (
            llm_parsed_context.get("intent")
            if isinstance(llm_parsed_context, dict)
            else None
        )
        if llm_intent == "casual_chat" and not (
            parsed and parsed.get("tool_name") == "search_restaurants"
        ):
            return {"tool_name": "casual_chat", "arguments": {}}

        if llm_intent == "search_restaurants":
            return {
                "tool_name": "search_restaurants",
                "arguments": {"user_id": user_id, "session_id": session_id},
            }

        return None

    def _select_from_pending_slots(
        self,
        state: AgentState,
        message: str,
        location: dict[str, Any] | None,
        user_id: str | None,
        session_id: str | None,
    ) -> dict[str, Any] | None:
        """如果上一轮在追问，本轮补齐地址或位置时直接继续搜索。"""
        pending_slots = state.get("short_term_memory", {}).get("pending_search_slots")
        if not isinstance(pending_slots, dict):
            return None

        supplied_slots = self.tool_registry.extract_slots(
            "search_restaurants",
            {**state, "message": message, "location": location},
        ).get("search_slots") or {}

        if supplied_slots.get("address") or supplied_slots.get("location"):
            return {
                "tool_name": "search_restaurants",
                "arguments": {"user_id": user_id, "session_id": session_id},
            }

        return None

    async def _select_by_llm_tool_call(
        self,
        state: AgentState,
    ) -> dict[str, Any] | None:
        """让 LLM 在业务级工具列表中选择工具，不暴露 MCP 原子工具。"""
        try:
            return await self.agent_llm_client.select_tool(
                message=state.get("message") or "",
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
                short_term_memory=state.get("short_term_memory", {}),
                long_term_memory={
                    **state.get("long_term_memory", {}),
                    "current_location": state.get("location"),
                    "location_label": state.get("location_label"),
                },
                tools=self.tool_registry.openai_tool_definitions(),
            )
        except Exception:
            return None

    @classmethod
    def _normalize_llm_parsed_context(
        cls,
        context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """清洗 LLM 解析结果，避免异常字段污染 Workflow state。"""
        if not isinstance(context, dict):
            return None

        normalized: dict[str, Any] = {}
        intent = clean_text(context.get("intent"))
        normalized["intent"] = (
            intent if intent in {"search_restaurants", "casual_chat", "unknown"} else "unknown"
        )

        for field in ("address", "city", "keyword", "cuisine", "scene"):
            value = clean_text(context.get(field))
            if value:
                normalized[field] = value

        for field in ("budget", "radius", "limit"):
            value = to_int(context.get(field))
            if value is not None:
                normalized[field] = value

        location = context.get("location")
        if isinstance(location, dict):
            longitude = to_float(location.get("longitude"))
            latitude = to_float(location.get("latitude"))
            if longitude is not None and latitude is not None:
                normalized["location"] = {
                    "longitude": longitude,
                    "latitude": latitude,
                }

        if bool(context.get("is_continue_recommendation")):
            normalized["is_continue_recommendation"] = True

        return normalized
