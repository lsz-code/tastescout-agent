from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentToolCall
from app.workflows.agent_workflow import AgentWorkflow


class AgentService:
    def __init__(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
    ) -> None:
        self.db = db
        self.short_term_memory = short_term_memory

    async def chat(self, payload: AgentChatRequest) -> AgentChatResponse:
        workflow = AgentWorkflow(
            db=self.db,
            short_term_memory=self.short_term_memory,
        )
        state = await workflow.run(
            user_id=payload.user_id,
            session_id=payload.session_id,
            message=payload.message,
            location=payload.location,
            location_label=payload.location_label,
        )

        return AgentChatResponse(
            user_id=payload.user_id,
            session_id=payload.session_id,
            reply=state.get("reply") or "我可以帮你搜索餐厅、收藏推荐结果、查看收藏夹或查看口味偏好。",
            intent=state.get("intent"),
            tool_calls=[
                AgentToolCall(**tool_call)
                for tool_call in state.get("tool_calls", [])
            ],
            data=state.get("data"),
            memory_used=bool(state.get("memory_used")),
        )
