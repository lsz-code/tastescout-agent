from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import tool_registry as default_tool_registry
from app.agent.intent_parser import IntentParser
from app.agent.llm_client import AgentLLMClient
from app.memory.short_term import ShortTermMemory
from app.workflows.agent_state import AgentState
from app.workflows.nodes import AgentWorkflowNodes

#Agent工作流
class AgentWorkflow:
    def __init__(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        agent_llm_client: AgentLLMClient | None = None,
        intent_parser: IntentParser | None = None,
        tool_registry: Any = None,
    ) -> None:
        self.nodes = AgentWorkflowNodes(
            db=db,
            short_term_memory=short_term_memory,
            agent_llm_client=agent_llm_client,
            intent_parser=intent_parser,
            tool_registry=tool_registry or default_tool_registry,
        )
        self.graph = self.build_graph()

    def build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("load_memory", self.nodes.load_memory)
        workflow.add_node("classify_intent", self.nodes.classify_intent)
        workflow.add_node("extract_slots", self.nodes.extract_slots)
        workflow.add_node("check_slots", self.nodes.check_slots)
        workflow.add_node("ask_followup", self.nodes.ask_followup)
        workflow.add_node("search_restaurants", self.nodes.search_restaurants)
        workflow.add_node("add_favorite", self.nodes.add_favorite)
        workflow.add_node("show_favorites", self.nodes.show_favorites)
        workflow.add_node("get_memory", self.nodes.get_memory)
        workflow.add_node("refresh_memory", self.nodes.refresh_memory)
        workflow.add_node("fallback", self.nodes.fallback)
        workflow.add_node("generate_response", self.nodes.generate_response)

        workflow.add_edge(START, "load_memory")
        workflow.add_edge("load_memory", "classify_intent")
        workflow.add_edge("classify_intent", "extract_slots")
        workflow.add_edge("extract_slots", "check_slots")

        workflow.add_conditional_edges(
            "check_slots",
            self._route_by_intent,
            {
                "ask_followup": "ask_followup",
                "search_restaurants": "search_restaurants",
                "add_favorite": "add_favorite",
                "show_favorites": "show_favorites",
                "get_memory": "get_memory",
                "refresh_memory": "refresh_memory",
                "fallback": "fallback",
            },
        )

        workflow.add_edge("ask_followup", "generate_response")
        workflow.add_edge("search_restaurants", "generate_response")
        workflow.add_edge("add_favorite", "generate_response")
        workflow.add_edge("show_favorites", "generate_response")
        workflow.add_edge("get_memory", "generate_response")
        workflow.add_edge("refresh_memory", "generate_response")
        workflow.add_edge("fallback", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    async def run(
        self,
        user_id: str,
        session_id: str,
        message: str,
        location: dict[str, Any] | None = None,
        location_label: str | None = None,
    ) -> AgentState:
        initial_state: AgentState = {
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
            "location": location,
            "location_label": location_label,
            "intent": None,
            "search_slots": None,
            "missing_slots": [],
            "short_term_memory": {},
            "long_term_memory": {},
            "tool_calls": [],
            "tool_result": None,
            "data": None,
            "reply": None,
            "error": None,
            "memory_used": False,
        }
        return await self.graph.ainvoke(initial_state)

    @staticmethod
    def _route_by_intent(state: AgentState) -> str:
        intent = state.get("intent")

        if intent == "search_restaurants" and state.get("missing_slots"):
            return "ask_followup"

        if intent == "search_restaurants":
            return "search_restaurants"

        if intent == "add_favorite_by_rank":
            return "add_favorite"

        if intent == "show_favorites":
            return "show_favorites"

        if intent == "get_user_memory":
            return "get_memory"

        if intent == "refresh_user_memory":
            return "refresh_memory"

        return "fallback"
