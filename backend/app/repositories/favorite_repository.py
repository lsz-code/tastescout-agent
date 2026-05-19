from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite_collection import FavoriteCollection
from app.models.favorite_restaurant import FavoriteRestaurant
from app.models.user import User


class FavoriteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_user_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    #收藏夹初始化
    async def create_collection(
        self,
        user_db_id: int,
        name: str,
        description: str | None = None,
    ) -> FavoriteCollection:
        collection = FavoriteCollection(
            user_id=user_db_id,
            name=name,
            description=description,
            is_default=False,
        )
        self.db.add(collection)
        await self.db.flush()
        return collection

    async def get_collections_by_user(
        self,
        user_db_id: int,
    ) -> list[tuple[FavoriteCollection, int]]:
        result = await self.db.execute(
            select(
                FavoriteCollection,
                func.count(FavoriteRestaurant.id).label("restaurant_count"),
            )
            .outerjoin(
                FavoriteRestaurant,
                FavoriteRestaurant.collection_id == FavoriteCollection.id,
            )
            .where(FavoriteCollection.user_id == user_db_id)
            .group_by(FavoriteCollection.id)
            .order_by(FavoriteCollection.is_default.desc(), FavoriteCollection.id.asc())
        )
        return [(collection, count) for collection, count in result.all()]

    async def get_default_collection(
        self,
        user_db_id: int,
    ) -> FavoriteCollection | None:
        result = await self.db.execute(
            select(FavoriteCollection).where(
                FavoriteCollection.user_id == user_db_id,
                FavoriteCollection.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_collection_by_id(
        self,
        collection_id: int,
    ) -> FavoriteCollection | None:
        result = await self.db.execute(
            select(FavoriteCollection).where(FavoriteCollection.id == collection_id)
        )
        return result.scalar_one_or_none()

    async def get_favorite_by_user_and_poi(
        self,
        user_db_id: int,
        poi_id: str,
    ) -> FavoriteRestaurant | None:
        result = await self.db.execute(
            select(FavoriteRestaurant).where(
                FavoriteRestaurant.user_id == user_db_id,
                FavoriteRestaurant.poi_id == poi_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_favorite(
        self,
        user_db_id: int,
        collection_id: int,
        poi_id: str,
        name: str,
        address: str | None = None,
        photo: str | None = None,
        location: dict[str, Any] | None = None,
        cuisine_type: str | None = None,
        rating: float | None = None,
        avg_price: int | None = None,
        distance: float | None = None,
        recommended_dishes: list[Any] | dict[str, Any] | None = None,
        review_summary: str | None = None,
        recommend_reason: str | None = None,
        raw_data: dict[str, Any] | None = None,
    ) -> FavoriteRestaurant:
        favorite = FavoriteRestaurant(
            user_id=user_db_id,
            collection_id=collection_id,
            poi_id=poi_id,
            name=name,
            address=address,
            photo=photo,
            location=location,
            cuisine_type=cuisine_type,
            rating=rating,
            avg_price=avg_price,
            distance=distance,
            recommended_dishes=recommended_dishes,
            review_summary=review_summary,
            recommend_reason=recommend_reason,
            raw_data=raw_data,
        )
        self.db.add(favorite)
        await self.db.flush()
        return favorite

    #获取用户收藏夹内的餐厅
    async def get_favorites_by_user(
        self,
        user_db_id: int,
        collection_id: int | None = None,
    ) -> list[FavoriteRestaurant]:
        statement = select(FavoriteRestaurant).where(
            FavoriteRestaurant.user_id == user_db_id
        )
        if collection_id is not None:
            statement = statement.where(FavoriteRestaurant.collection_id == collection_id)

        result = await self.db.execute(statement.order_by(FavoriteRestaurant.id.desc()))
        return list(result.scalars().all())

    #根据id获取收藏夹内的餐厅
    async def get_favorite_by_id(
        self,
        favorite_id: int,
    ) -> FavoriteRestaurant | None:
        result = await self.db.execute(
            select(FavoriteRestaurant).where(FavoriteRestaurant.id == favorite_id)
        )
        return result.scalar_one_or_none()

    async def delete_favorite(self, favorite: FavoriteRestaurant) -> None:
        await self.db.delete(favorite)
        await self.db.flush()
