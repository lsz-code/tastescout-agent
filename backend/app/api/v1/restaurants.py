from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.memory.short_term import ShortTermMemory, get_short_term_memory
from app.schemas.restaurant import (
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)
from app.services.restaurant_search_service import RestaurantSearchService


router = APIRouter(prefix="/restaurants", tags=["Restaurants"])

@router.post("/search", response_model=RestaurantSearchResponse)
async def search_restaurants(
    payload:RestaurantSearchRequest,
    db:AsyncSession = Depends(get_db),
    short_term_memory:ShortTermMemory = Depends(get_short_term_memory),
)->RestaurantSearchResponse:
    service = RestaurantSearchService(
        db=db,
        short_term_memory=short_term_memory,
    )

    try:
        return await service.search(payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc