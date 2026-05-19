from fastapi import APIRouter, Depends,HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.memory.short_term import ShortTermMemory,get_short_term_memory
from app.schemas.memory import(
    AppendCandidateRequest,
    LongTermMemoryResponse,
    LongTermMemoryData,
    RefreshLongTermMemoryResponse,
    MemoryOperationResponse,
    ShortTermMemoryResponse,
    ShortTermMemorySetRequest,
    ShortTermMemoryUpdateRequest,
)
from app.services.memory_service import MemoryService


router = APIRouter(prefix="/memory",tags=["memory"])

#根据session_id获取短期记忆接口
@router.get(
    "/short-term/{session_id}",
    response_model=ShortTermMemoryResponse,
)
async def get_short_term_memory_by_session(
    session_id: str,
    memory: ShortTermMemory = Depends(get_short_term_memory),
)->ShortTermMemoryResponse:
    try:
        data=await memory.get(session_id)
        return ShortTermMemoryResponse(
            session_id=session_id,
            memory=data,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

#设置短期记忆接口
@router.put(
    "/short-term",
    response_model=MemoryOperationResponse,
)
async def set_short_term_memory(
    payload: ShortTermMemorySetRequest,
    memory: ShortTermMemory = Depends(get_short_term_memory),
)->MemoryOperationResponse:
    try:
        data = dict(payload.data)
        if payload.user_id is not None:
            data["user_id"] = payload.user_id

        print("redis key =", payload.session_id)
        print("redis value =", data)
        updated_memory = await memory.set(payload.session_id,data)
        return MemoryOperationResponse(
            success=True,
            message="短期记忆已设置",
            memory=updated_memory,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )from exc
    
#更新短期记忆到redis
@router.patch(
    "/short-term",
    response_model=MemoryOperationResponse,
)
async def update_short_term_memory(
    payload: ShortTermMemoryUpdateRequest,
    memory: ShortTermMemory = Depends(get_short_term_memory),
) -> MemoryOperationResponse:
    try:
        updated_memory = await memory.update(payload.session_id,payload.patch)
        return MemoryOperationResponse(
            success=True,
            message="短期记忆已更新",
            memory=updated_memory,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

#删除整个会话对应的redis中的短期记忆接口
@router.delete(
    "/short-term/{session_id}",
    response_model=MemoryOperationResponse,
)
async def delete_short_term_memory(
    session_id:str,
    memory: ShortTermMemory = Depends(get_short_term_memory),
) -> MemoryOperationResponse:
    try:
        deleted = await memory.delete(session_id)
        return MemoryOperationResponse(
            success=deleted,
            message="短期记忆已删除" if deleted else "短期记忆不存在",
            memory=None,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    
#追加候选餐厅到短期记忆
@router.post(
    "/short-term/candidates",
    response_model=MemoryOperationResponse,
)
async def append_short_term_candidates(
    payload:AppendCandidateRequest,
    memory:ShortTermMemory = Depends(get_short_term_memory),
)-> MemoryOperationResponse:
    try:
        updated_memory = await memory.append_candidates(
            payload.session_id,
            payload.restaurant,
        )
        return MemoryOperationResponse(
            success=True,
            message="候选餐厅已追加",
            memory=updated_memory,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )from exc

#清空候选餐厅接口
@router.delete(
    "/short-term/{session_id}/candidates",
    response_model=MemoryOperationResponse,
)
async def clear_short_term_candidates(
    session_id:str,
    memory: ShortTermMemory = Depends(get_short_term_memory),
) -> MemoryOperationResponse:
    try:
        updated_memory = await memory.clear_candiates(session_id)
        return MemoryOperationResponse(
            success=True,
            message="候选餐厅已清空",
            memory=updated_memory,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )from exc

#根据user_id获取长期记忆接口
@router.get(
    "/long-term/{user_id}",
    response_model=LongTermMemoryResponse,
)
async def get_long_term_memory(
    user_id:str,
    db:AsyncSession = Depends(get_db), 
)-> LongTermMemoryResponse:
    service = MemoryService(db)

    #这个涉及到访问postgres数据库，所以需要有service层来处理业务逻辑，最终调用repository层来访问数据库
    return await service.get_long_term_memory(user_id)

#刷新用户长期记忆接口
@router.post(
    "/long-term/{user_id}/refresh",
    response_model=RefreshLongTermMemoryResponse,
)
async def refresh_long_term_memory(
    user_id:str,
    db:AsyncSession= Depends(get_db),
)-> RefreshLongTermMemoryResponse:
    service = MemoryService(db)
    return await service.refresh_long_term_memory(user_id)