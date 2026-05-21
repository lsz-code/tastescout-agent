from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.memory.short_term import ShortTermMemory, get_short_term_memory
from app.schemas.restaurant import (
    CreateReviewRequest,
    RestaurantDetailResponse,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
    ReviewResponse,
    UpsertRestaurantRequest,
)
from app.services.restaurant_search_service import RestaurantSearchService
from app.services.restaurant_service import RestaurantService


router = APIRouter(prefix="/restaurants", tags=["Restaurants"])

#餐厅查找接口
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

#餐厅信息补充接口，根据用户提供的餐厅信息进行餐厅记录的创建或更新，并返回餐厅详情信息。
@router.post("", response_model=RestaurantDetailResponse)
async def upsert_restaurant(
    payload: UpsertRestaurantRequest,
    db: AsyncSession = Depends(get_db),
) -> RestaurantDetailResponse:
    service = RestaurantService(db)
    return await service.upsert_restaurant(payload)

#获取餐厅详细信息，根据餐厅的poi_id查询餐厅的基本信息和用户评论列表，并返回给客户端。
@router.get("/{poi_id}", response_model=RestaurantDetailResponse)
async def get_restaurant_detail(
    poi_id: str,
    db: AsyncSession = Depends(get_db),
) -> RestaurantDetailResponse:
    service = RestaurantService(db)
    return await service.get_restaurant_detail(poi_id)

#创建或更新用户评论接口，根据用户提供的评论内容和评分信息，创建或更新用户对指定餐厅的评论记录，并返回评论详情信息。
@router.post("/{poi_id}/reviews", response_model=ReviewResponse)
async def create_or_update_review(
    poi_id: str,
    payload: CreateReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    service = RestaurantService(db)
    return await service.create_or_update_review(poi_id, payload)
