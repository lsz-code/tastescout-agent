from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.restaurant import Restaurant
from app.models.reviews import Review
from app.models.user import User


# 餐厅相关的数据访问层，提供与餐厅和评论相关的数据库操作方法。

class RestaurantRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_user_id(self, user_id: str) -> User | None:
        """根据用户ID获取用户信息"""
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_poi_id(self, poi_id: str) -> Restaurant | None:
        """根据POI ID获取餐厅信息"""
        result = await self.db.execute(
            select(Restaurant).where(Restaurant.poi_id == poi_id)
        )
        return result.scalar_one_or_none()

    async def get_detail_by_poi_id(self, poi_id: str) -> Restaurant | None:
        """获取餐厅详细信息，包括评论和评论用户信息"""
        result = await self.db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.reviews).selectinload(Review.user))
            .where(Restaurant.poi_id == poi_id)
        )
        return result.scalar_one_or_none()

    async def create_restaurant(self, **values) -> Restaurant:
        """创建餐厅记录，并提交到数据库"""
        restaurant = Restaurant(**values)
        self.db.add(restaurant)
        await self.db.flush()
        return restaurant

    async def get_review_by_restaurant_and_user(
        self,
        restaurant_id: int,
        user_db_id: int,
    ) -> Review | None:
        """根据餐厅ID和用户数据库ID获取评论记录"""
        result = await self.db.execute(
            select(Review).where(
                Review.restaurant_id == restaurant_id,
                Review.user_id == user_db_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_review(
        self,
        restaurant_id: int,
        user_db_id: int,
        content: str,
        rating: float | None,
    ) -> Review:
        """创建评论记录，并提交到数据库"""
        review = Review(
            restaurant_id=restaurant_id,
            user_id=user_db_id,
            content=content,
            rating=rating,
        )
        self.db.add(review)
        await self.db.flush()
        return review
