from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite_restaurant import FavoriteRestaurant
from app.models.user import User
from app.models.user_memory import UserMemory
from app.schemas.memory import LongTermMemoryData

#长期记忆存储库操作方法
class MemoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    #从postgres中获取user
    async def get_user_by_user_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()
    
    #根据user_id获取长期记忆
    async def get_memory_by_user_id(self,user_db_id:int)->UserMemory | None:
        result = await self.db.execute(
            select(UserMemory).where(UserMemory.user_id == user_db_id)
        )
        return result.scalar_one_or_none()
    
    #创建一个空的长期记忆
    async def create_empty_memory(self,user_db_id:int)->UserMemory:
        memory = UserMemory(
            user_id=user_db_id,
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
    
    #从postgres中根据用户id获取收藏夹餐厅
    async def get_favorite_restaurants_by_user_id(
            self,
            user_db_id: int,
    )->list[FavoriteRestaurant]:
        result = await self.db.execute(
            select(FavoriteRestaurant).where(FavoriteRestaurant.user_id == user_db_id)
        )
        return list(result.scalars().all())
    
    #更新长期记忆到postgres数据库
    async def update_user_memory(
            self,
            memory_orm:UserMemory,
            memory_data:LongTermMemoryData,
    ) -> UserMemory:
        memory_orm.favorite_cuisines = memory_data.favorite_cuisines
        memory_orm.taste_preference = memory_data.taste_preference
        memory_orm.avoid_foods = memory_data.avoid_foods
        memory_orm.price_preference = memory_data.price_preference.model_dump(
            exclude_none=True
        )
        memory_orm.favorite_dishes = memory_data.favorite_dishes
        memory_orm.preferred_scenes = memory_data.preferred_scenes
        memory_orm.memory_summary = memory_data.memory_summary
        memory_orm.source_version = memory_data.source_version

        await self.db.flush()
        return memory_orm
    
          