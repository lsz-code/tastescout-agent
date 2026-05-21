from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.favorite import (
    AddFavoriteRestaurantRequest,
    AddFavoriteRestaurantResponse,
    CreateFavoriteCollectionRequest,
    DeleteFavoriteResponse,
    FavoriteCollectionResponse,
    FavoriteRestaurantResponse,
)
from app.services.favorite_service import FavoriteService


router = APIRouter(tags=["Favorites"])

#收藏夹创建与初始化
@router.post(
    "/favorite-collections",
    response_model=FavoriteCollectionResponse,
)
async def create_favorite_collection(
    payload: CreateFavoriteCollectionRequest,
    db: AsyncSession = Depends(get_db),
) -> FavoriteCollectionResponse:
    service = FavoriteService(db)
    return await service.create_collection(payload)


#收藏夹列表查询
@router.get(
    "/favorite-collections",
    response_model=list[FavoriteCollectionResponse],
)
async def list_favorite_collections(
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[FavoriteCollectionResponse]:
    service = FavoriteService(db)
    return await service.list_collections(user_id)

#收藏餐厅添加
@router.post("/favorites", response_model=AddFavoriteRestaurantResponse)
async def add_favorite_restaurant(
    payload: AddFavoriteRestaurantRequest,
    db: AsyncSession = Depends(get_db),
) -> AddFavoriteRestaurantResponse:
    service = FavoriteService(db)
    return await service.add_favorite(payload=payload)

#查询收藏的所有餐厅
@router.get("/favorites", response_model=list[FavoriteRestaurantResponse])
async def list_favorite_restaurants(
    user_id: str = Query(...),
    collection_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[FavoriteRestaurantResponse]:
    service = FavoriteService(db)
    return await service.list_favorites(
        user_id=user_id,
        collection_id=collection_id,
    )

#删除收藏夹
@router.delete("/favorites/{favorite_id}", response_model=DeleteFavoriteResponse)
async def delete_favorite_restaurant(
    favorite_id: int,
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> DeleteFavoriteResponse:
    service = FavoriteService(db)
    return await service.delete_favorite(
        user_id=user_id,
        favorite_id=favorite_id,
    )


