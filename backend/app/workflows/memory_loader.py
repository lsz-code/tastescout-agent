from typing import Any

from app.memory.short_term import ShortTermMemory
from app.schemas.memory import LongTermMemoryData
from app.services.memory_service import MemoryService
from app.workflows.agent_state import AgentState
from app.workflows.state_utils import missing_required_field


class MemoryLoader:
    """负责把短期记忆和长期记忆加载进 LangGraph state。"""

    def __init__(
        self,
        short_term_memory: ShortTermMemory,
        memory_service: MemoryService,
    ) -> None:
        """保存记忆访问依赖，避免节点层直接关心 Redis/PostgreSQL 细节。"""
        self.short_term_memory = short_term_memory
        self.memory_service = memory_service

    async def load(self, state: AgentState) -> dict[str, Any]:
        """读取当前会话短期记忆和当前用户长期记忆。"""
        missing_error = missing_required_field(state)
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
            #短期记忆，以对话id作为索引获取
            short_term_memory = await self.short_term_memory.get(session_id)
            #长期记忆以用户id作为索引获取
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
