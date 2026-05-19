from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.memory.short_term import ShortTermMemory, get_short_term_memory
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    payload:AgentChatRequest,
    db:AsyncSession = Depends(get_db),
    short_term_memory: ShortTermMemory = Depends(get_short_term_memory),
)->AgentChatResponse:
    service = AgentService(
        db=db,
        short_term_memory=short_term_memory,
    )

    try:
        return await service.chat(payload)
    
    except RuntimeError as exc:
        raise HTTPException (
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
