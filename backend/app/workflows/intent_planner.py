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
    """Plan the next business intent and tool arguments from user input."""

    def __init__(
        self,
        agent_llm_client: AgentLLMClient,
        intent_parser: IntentParser,
        tool_registry: Any,
    ) -> None:
        self.agent_llm_client = agent_llm_client
        self.intent_parser = intent_parser
        self.tool_registry = tool_registry

    async def plan(self, state: AgentState) -> dict[str, Any]:
        """Use direct rules first, then one structured LLM parse, then rule fallback."""
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

        direct_result = self._try_rule_direct_intent(parsed, state)
        if direct_result is not None:
            return direct_result

        llm_parsed_context = await self._extract_llm_context(state)

        #下面_select_from_llm_context的作用是根据llm_parsed_context和parsed来选择最终的意图和参数
        selected = self._select_from_llm_context(
            llm_parsed_context=llm_parsed_context,
            parsed=parsed,
            user_id=user_id,
            session_id=session_id,
        )

        #如果llm_parsed_context和parsed都没有提供明确的意图，那么就尝试从pending_slots中选择意图
        if selected is None:
            selected = self._select_from_pending_slots(
                state=state,
                message=message,
                location=location,
                user_id=user_id,
                session_id=session_id,
            )

        #如果selected仍然为None，那么就使用parsed作为最终的意图和参数
        if selected is None:
            selected = parsed

        if selected is None:
            return {
                "intent": "fallback",
                "planned_tool_args": {},
                "llm_parsed_context": llm_parsed_context,
            }

        #如果selected不为None，那么就使用selected中的tool_name和arguments作为最终的意图和参数
        tool_name = selected.get("tool_name") or "fallback"
        arguments = self.tool_registry.prepare_arguments(
            tool_name=tool_name,
            arguments=selected.get("arguments") or {},
            state=state,
        )

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
        """Return immediately for high-confidence rule intents."""
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
        """Call the structured context parser once for intent and slot extraction."""
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
        """Map the structured LLM intent to a business tool."""
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
        """Continue a pending restaurant search when the user supplies location."""
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

    @classmethod
    def _normalize_llm_parsed_context(
        cls,
        context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Normalize LLM output before writing it into workflow state."""
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
