from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import UserBootstrapRequest, UserBootstrapResponse
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/bootstrap", response_model=UserBootstrapResponse)
async def bootstrap_user(
    payload: UserBootstrapRequest,
    db: AsyncSession = Depends(get_db),
) -> UserBootstrapResponse:
    service = UserService(db)
    return await service.bootstrap_user(payload)
