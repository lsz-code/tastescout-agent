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
    # 获取用户信息
    async def get_user_by_user_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    # 根据POI ID获取餐厅信息
    async def get_by_poi_id(self, poi_id: str) -> Restaurant | None:
        result = await self.db.execute(
            select(Restaurant).where(Restaurant.poi_id == poi_id)
        )
        return result.scalar_one_or_none()

    # 根据POI ID获取餐厅评论信息
    async def get_detail_by_poi_id(self, poi_id: str) -> Restaurant | None:
        result = await self.db.execute(
            select(Restaurant)
            .options(selectinload(Restaurant.reviews).selectinload(Review.user))
            .where(Restaurant.poi_id == poi_id)
        )
        return result.scalar_one_or_none()

    # 创建餐厅记录
    async def create_restaurant(self, **values) -> Restaurant:
        restaurant = Restaurant(**values)
        self.db.add(restaurant)
        await self.db.flush()
        return restaurant

    # 通过餐厅和用户ID获取评论信息
    async def get_review_by_restaurant_and_user(
        self,
        restaurant_id: int,
        user_db_id: int,
    ) -> Review | None:
        result = await self.db.execute(
            select(Review).where(
                Review.restaurant_id == restaurant_id,
                Review.user_id == user_db_id,
            )
        )
        return result.scalar_one_or_none()

    #创建评论记录，提交到数据库
    async def create_review(
        self,
        restaurant_id: int,
        user_db_id: int,
        content: str,
        rating: float | None,
    ) -> Review:
        review = Review(
            restaurant_id=restaurant_id,
            user_id=user_db_id,
            content=content,
            rating=rating,
        )
        self.db.add(review)
        await self.db.flush()
        return review
