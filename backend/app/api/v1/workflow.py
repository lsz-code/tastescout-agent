from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.memory.short_term import ShortTermMemory, get_short_term_memory
from app.schemas.agent import AgentChatRequest
from app.workflows.agent_workflow import AgentWorkflow


router = APIRouter(prefix="/workflow", tags=["Workflow"])

#工作流调试接口，这个接口直接返回LangGraph的完整state，前端可以根据这个state来展示agent的思考过程和行动决策。
@router.post("/debug-agent")
async def debug_agent_workflow(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    short_term_memory: ShortTermMemory = Depends(get_short_term_memory),
) -> dict[str, Any]:
    workflow = AgentWorkflow(
        db=db,
        short_term_memory=short_term_memory,
    )

    try:
        return await workflow.run(
            user_id=payload.user_id,
            session_id=payload.session_id,
            message=payload.message,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
