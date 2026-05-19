from collections import Counter
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite_restaurant import FavoriteRestaurant
from app.models.user import User
from app.models.user_memory import UserMemory
from app.repositories.memory_repository import MemoryRepository
from app.schemas.memory import (
    LongTermMemoryData,
    LongTermMemoryResponse,
    PricePreference,
    RefreshLongTermMemoryResponse,
)

class MemoryService:
    TASTE_KEYWORDS = ["偏辣", "清淡", "重口味", "性价比高", "分量大", "环境好"]
    SCENE_KEYWORDS = ["一人食", "两人用餐", "朋友聚餐", "家庭聚餐", "夜宵", "约会"]
    def __init__(self, db: AsyncSession):
        self.db = db
        #在service层中实例化repository层，repository层负责访问数据库
        self.memory_repository = MemoryRepository(db)
    
    #获取长期记忆，构建搜索上下文
    async def get_long_term_memory(self, user_id: str) -> LongTermMemoryResponse:
        try:
            user = await self._get_existing_user(user_id)
            memory = await self.memory_repository.get_memory_by_user_id(user.id)

            if memory is None:
                memory = await self.memory_repository.create_empty_memory(user.id)
                await self.db.commit()
                await self.db.refresh(memory)
            return self._build_response(user, memory)

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    #刷新长期记忆
    async def refresh_long_term_memory(
        self,
        user_id: str,
    ) -> RefreshLongTermMemoryResponse:
        try:
            #存在性校验
            user = await self._get_existing_user(user_id)
            memory = await self.memory_repository.get_memory_by_user_id(user.id)

            if memory is None:
                memory = await self.memory_repository.create_empty_memory(user.id)

            #根据用户id获取收藏夹
            favorites = await self.memory_repository.get_favorite_restaurants_by_user_id(
                user.id
            )

            #根据收藏夹总结用户偏好，构建长期记忆数据
            memory_data = self._summarize_favorites(favorites, memory)

            #更新用户长期记忆
            memory = await self.memory_repository.update_user_memory(
                memory_orm=memory,
                memory_data=memory_data,
            )

            await self.db.commit()
            await self.db.refresh(memory)

            return RefreshLongTermMemoryResponse(
                success=True,
                message="长期 Memory 已刷新",
                memory=self._build_response(user, memory),
            )

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise
    
    # 判断用户是否存在
    async def _get_existing_user(self, user_id: str) -> User:
        user = await self.memory_repository.get_user_by_user_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return user

    def _summarize_favorites(
        self,
        favorites: list[FavoriteRestaurant],
        old_memory: UserMemory,
    ) -> LongTermMemoryData:
        avoid_foods = self._as_str_list(old_memory.avoid_foods)
        next_version = (old_memory.source_version or 0) + 1

        if not favorites:
            return LongTermMemoryData(
                avoid_foods=avoid_foods,
                memory_summary="暂无收藏数据，暂时无法总结用户偏好。",
                source_version=next_version,
            )
        
        favorite_cuisines = self._top_cuisines(favorites)
        favorite_dishes = self._top_dishes(favorites)
        price_preference = self._build_price_preference(favorites)
        taste_preference = self._extract_keywords(favorites, self.TASTE_KEYWORDS)
        preferred_scenes = self._extract_keywords(favorites, self.SCENE_KEYWORDS)

        return LongTermMemoryData(
            favorite_cuisines=favorite_cuisines,
            taste_preference=taste_preference,
            avoid_foods=avoid_foods,
            price_preference=price_preference,
            favorite_dishes=favorite_dishes,
            preferred_scenes=preferred_scenes,
            memory_summary=self._build_memory_summary(
                favorite_cuisines=favorite_cuisines,
                price_preference=price_preference,
                taste_preference=taste_preference,
                preferred_scenes=preferred_scenes,
            ),
            source_version=next_version,
        )

    #获取top-k偏好菜系
    def _top_cuisines(self, favorites: list[FavoriteRestaurant]) -> list[str]:
        counter = Counter(
            favorite.cuisine_type.strip()
            for favorite in favorites
            if favorite.cuisine_type and favorite.cuisine_type.strip()
        )
        return [name for name, _ in counter.most_common(5)]

    #获取top-k偏好菜品
    def _top_dishes(self, favorites: list[FavoriteRestaurant]) -> list[str]:
        counter: Counter[str] = Counter()

        for favorite in favorites:
            dishes = favorite.recommended_dishes or []
            if isinstance(dishes, dict):
                dishes = [dishes]

            for dish in dishes:
                dish_name = self._extract_dish_name(dish)
                if dish_name:
                    counter[dish_name] += 1

        return [name for name, _ in counter.most_common(10)]

    #提取菜品名称
    def _extract_dish_name(self, dish: Any) -> str | None:
        if isinstance(dish, str):
            return dish.strip() or None

        if isinstance(dish, dict):
            value = dish.get("dish_name") or dish.get("name")
            if isinstance(value, str):
                return value.strip() or None

        return None

    #构建价格偏好
    def _build_price_preference(
        self,
        favorites: list[FavoriteRestaurant],
    ) -> PricePreference:
        prices = [
            favorite.avg_price
            for favorite in favorites
            if favorite.avg_price is not None
        ]

        if not prices:
            return PricePreference()

        return PricePreference(
            min_price=min(prices),
            max_price=max(prices),
            avg_price=round(sum(prices) / len(prices), 2),
        )

    #提取关键词
    def _extract_keywords(
        self,
        favorites: list[FavoriteRestaurant],
        keywords: list[str],
    ) -> list[str]:
        counter: Counter[str] = Counter()

        for favorite in favorites:
            text = " ".join(
                item
                for item in [favorite.review_summary, favorite.recommend_reason]
                if item
            )
            for keyword in keywords:
                if keyword in text:
                    counter[keyword] += 1

        return [keyword for keyword, _ in counter.most_common()]

    #构建记忆总结
    def _build_memory_summary(
        self,
        favorite_cuisines: list[str],
        price_preference: PricePreference,
        taste_preference: list[str],
        preferred_scenes: list[str],
    ) -> str:
        parts = []

        if favorite_cuisines:
            parts.append(f"用户偏好{self._join_cn(favorite_cuisines[:3])}")

        if (
            price_preference.min_price is not None
            and price_preference.max_price is not None
        ):
            parts.append(
                f"常收藏人均 {price_preference.min_price}-{price_preference.max_price} 元的餐厅"
            )

        preference_parts = taste_preference[:3] + preferred_scenes[:2]
        if preference_parts:
            parts.append(f"喜欢{self._join_cn(preference_parts)}的餐厅")

        if not parts:
            return "用户已有收藏数据，但暂未总结出明显偏好。"

        return "，".join(parts) + "。"

    #构建长期记忆响应
    def _build_response(
        self,
        user: User,
        memory: UserMemory,
    ) -> LongTermMemoryResponse:
        return LongTermMemoryResponse(
            user_id=user.user_id,
            memory=LongTermMemoryData(
                favorite_cuisines=self._as_str_list(memory.favorite_cuisines),
                taste_preference=self._as_str_list(memory.taste_preference),
                avoid_foods=self._as_str_list(memory.avoid_foods),
                price_preference=self._as_price_preference(memory.price_preference),
                favorite_dishes=self._as_str_list(memory.favorite_dishes),
                preferred_scenes=self._as_str_list(memory.preferred_scenes),
                memory_summary=memory.memory_summary or "",
                source_version=memory.source_version or 1,
            ),
            updated_at=memory.updated_at,
        )

    def _as_str_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    def _as_price_preference(self, value: Any) -> PricePreference:
        if not isinstance(value, dict):
            return PricePreference()
        return PricePreference(
            min_price=value.get("min_price"),
            max_price=value.get("max_price"),
            avg_price=value.get("avg_price"),
        )

    def _join_cn(self, items: list[str]) -> str:
        return "、".join(items)