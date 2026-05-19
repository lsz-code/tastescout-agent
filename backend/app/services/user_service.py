from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserBootstrapRequest, UserBootstrapResponse


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)

    async def bootstrap_user(
        self,
        payload: UserBootstrapRequest,
    ) -> UserBootstrapResponse:
        try:
            user = await self.user_repository.get_by_user_id(payload.user_id)
            is_new_user = user is None

            if user is None:
                user = await self.user_repository.create_user(
                    user_id=payload.user_id,
                    username=payload.username,
                    avatar_url=payload.avatar_url,
                )

            default_collection = await self.user_repository.get_default_collection(user)
            if default_collection is None:
                default_collection = (
                    await self.user_repository.create_default_collection(user)
                )

            user_memory = await self.user_repository.get_user_memory(user)
            if user_memory is None:
                user_memory = await self.user_repository.create_user_memory(user)

            await self.db.commit()
            await self.db.refresh(user)
            await self.db.refresh(default_collection)

            return UserBootstrapResponse(
                user_id=user.user_id,
                username=user.username,
                default_collection_id=default_collection.id,
                memory_initialized=user_memory is not None,
                is_new_user=is_new_user,
            )

        except Exception:
            await self.db.rollback()
            raise
