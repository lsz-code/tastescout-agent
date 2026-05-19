from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite_collection import FavoriteCollection
from app.models.user import User
from app.models.user_memory import UserMemory


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        user_id: str,
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        user = User(
            user_id=user_id,
            username=username,
            avatar_url=avatar_url,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_default_collection(self, user: User) -> FavoriteCollection | None:
        result = await self.db.execute(
            select(FavoriteCollection).where(
                FavoriteCollection.user_id == user.id,
                FavoriteCollection.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create_default_collection(self, user: User) -> FavoriteCollection:
        collection = FavoriteCollection(
            user_id=user.id,
            name="默认收藏夹",
            is_default=True,
        )
        self.db.add(collection)
        await self.db.flush()
        return collection

    async def get_user_memory(self, user: User) -> UserMemory | None:
        result = await self.db.execute(
            select(UserMemory).where(UserMemory.user_id == user.id)
        )
        return result.scalar_one_or_none()

    async def create_user_memory(self, user: User) -> UserMemory:
        memory = UserMemory(
            user_id=user.id,
            favorite_cuisines=[],
            taste_preference=[],
            avoid_foods=[],
            price_preference={},
            favorite_dishes=[],
            preferred_scenes=[],
            memory_summary="",
            source_version=1,
        )
        self.db.add(memory)
        await self.db.flush()
        return memory
