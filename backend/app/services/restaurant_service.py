from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant
from app.models.reviews import Review
from app.models.user import User
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import (
    CreateReviewRequest,
    RestaurantDetailResponse,
    ReviewResponse,
    UpsertRestaurantRequest,
)

#与参观相关的业务逻辑处理服务类，负责处理餐厅信息的创建、更新和查询，以及用户评论的创建和更新。

class RestaurantService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.restaurant_repository = RestaurantRepository(db)
    #提供餐厅信息的补充，如果餐厅不存在则创建新的餐厅记录，如果餐厅已存在则更新餐厅信息，并返回餐厅详情信息。
    async def upsert_restaurant(
        self,
        payload: UpsertRestaurantRequest,
    ) -> RestaurantDetailResponse:
        try:
            restaurant = await self.restaurant_repository.get_by_poi_id(payload.poi_id)
            values = payload.model_dump()

            if restaurant is None:
                restaurant = await self.restaurant_repository.create_restaurant(**values)
            else:
                self._update_restaurant(restaurant, values)
                await self.db.flush()

            await self.db.commit()
            return await self.get_restaurant_detail(payload.poi_id)
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise
    
    #根据POI ID获取餐厅详情信息，包括餐厅的基本信息和用户评论列表。
    async def get_restaurant_detail(self, poi_id: str) -> RestaurantDetailResponse:
        restaurant = await self.restaurant_repository.get_detail_by_poi_id(poi_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="餐厅不存在",
            )
        return self._build_detail_response(restaurant)

    #创建或更新用户的评论
    async def create_or_update_review(
        self,
        poi_id: str,
        payload: CreateReviewRequest,
    ) -> ReviewResponse:
        try:
            restaurant = await self.restaurant_repository.get_by_poi_id(poi_id)
            if restaurant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="餐厅不存在",
                )

            user = await self._get_existing_user(payload.user_id)
            review = await self.restaurant_repository.get_review_by_restaurant_and_user(
                restaurant_id=restaurant.id,
                user_db_id=user.id,
            )
            if review is None:
                review = await self.restaurant_repository.create_review(
                    restaurant_id=restaurant.id,
                    user_db_id=user.id,
                    content=payload.content,
                    rating=payload.rating,
                )
            else:
                review.content = payload.content
                review.rating = payload.rating
                await self.db.flush()
            review.user = user

            await self.db.commit()
            await self.db.refresh(review)
            review.user = user
            return self._build_review_response(review)
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise
    #获取已经存在的用户，如果不存在，抛出异常
    async def _get_existing_user(self, user_id: str) -> User:
        user = await self.restaurant_repository.get_user_by_user_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return user

    #更新餐厅信息
    @staticmethod
    def _update_restaurant(
        restaurant: Restaurant,
        values: dict[str, Any],
    ) -> None:
        for field, value in values.items():
            if field == "poi_id":
                continue
            if value is not None and value != "":
                setattr(restaurant, field, value)

    #构建餐厅查询回应
    def _build_detail_response(
        self,
        restaurant: Restaurant,
    ) -> RestaurantDetailResponse:
        reviews = sorted(
            restaurant.reviews,
            key=lambda item: item.created_at,
            reverse=True,
        )
        return RestaurantDetailResponse(
            id=restaurant.id,
            poi_id=restaurant.poi_id,
            name=restaurant.name,
            address=restaurant.address,
            photo=restaurant.photo,
            location=restaurant.location,
            cuisine_type=restaurant.cuisine_type,
            rating=restaurant.rating,
            avg_price=restaurant.avg_price,
            raw_data=restaurant.raw_data,
            reviews=[self._build_review_response(review) for review in reviews],
            created_at=restaurant.created_at,
            updated_at=restaurant.updated_at,
        )

    #构建评论回应
    @staticmethod
    def _build_review_response(review: Review) -> ReviewResponse:
        return ReviewResponse(
            id=review.id,
            restaurant_id=review.restaurant_id,
            user_id=review.user.user_id,
            username=review.user.username,
            content=review.content,
            rating=review.rating,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
