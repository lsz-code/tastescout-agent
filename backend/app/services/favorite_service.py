from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status

from app.guardrails.database_write_guard import DatabaseWriteGuard
from app.models.favorite_collection import FavoriteCollection
from app.models.favorite_restaurant import FavoriteRestaurant
from app.models.user import User
from app.services.memory_service import MemoryService 

from app.repositories.favorite_repository import FavoriteRepository
from app.schemas.favorite import (
    AddFavoriteRestaurantRequest,
    AddFavoriteRestaurantResponse,
    CreateFavoriteCollectionRequest,
    DeleteFavoriteResponse,
    FavoriteCollectionResponse,
    FavoriteRestaurantResponse,
)


class FavoriteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.favorite_repository = FavoriteRepository(db)

    async def create_collection(
        self,
        payload: CreateFavoriteCollectionRequest,
    ) -> FavoriteCollectionResponse:
        try:
            #检测用户存在
            user = await self._get_existing_user(payload.user_id)
            #
            collection = await self.favorite_repository.create_collection(
                user_db_id=user.id,
                name=payload.name,
                description=payload.description,
            )

            await self.db.commit()
            await self.db.refresh(collection)

            return self._build_collection_response(
                collection=collection,
                restaurant_count=0,
            )

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    #如果用户不存在则抛出异常，如果用户存在则查询用户的收藏夹列表，并构建返回格式
    async def list_collections(self, user_id: str) -> list[FavoriteCollectionResponse]:
        user = await self._get_existing_user(user_id)
        collections = await self.favorite_repository.get_collections_by_user(user.id)
        return [
            self._build_collection_response(
                collection=collection,
                restaurant_count=restaurant_count,
            )
            for collection, restaurant_count in collections
        ]

    #添加餐厅到收藏夹
    async def add_favorite(
        self,
        payload: AddFavoriteRestaurantRequest,
    ) -> AddFavoriteRestaurantResponse:
        try:
            user = await self._get_existing_user(payload.user_id)
            cleaned = DatabaseWriteGuard.validate_favorite_restaurant(
                payload.model_dump()
            )
            target_collection = None
            if payload.collection_id is not None or payload.collection_name:
                target_collection = await self._resolve_collection(
                    user=user,
                    collection_id=payload.collection_id,
                    collection_name=payload.collection_name,
                )

            existing_favorite = (
                await self.favorite_repository.get_favorite_by_user_and_poi(
                    user_db_id=user.id,
                    poi_id=cleaned["poi_id"],
                )
            )
            if existing_favorite is not None:
                changed = self._update_existing_favorite(
                    favorite=existing_favorite,
                    values=cleaned,
                    collection_id=(
                        target_collection.id
                        if target_collection is not None
                        else existing_favorite.collection_id
                    ),
                )
                if changed:
                    await self.db.flush()
                await self.db.commit()
                if changed:
                    await self.db.refresh(existing_favorite)
                    await self._refresh_memory_after_commit(user.user_id)
                return AddFavoriteRestaurantResponse(
                    success=True,
                    already_exists=True,
                    favorite_id=existing_favorite.id,
                    message="餐厅已收藏，已更新收藏信息" if changed else "餐厅已收藏",
                )

            collection = target_collection or await self._resolve_collection(
                user=user,
                collection_id=payload.collection_id,
                collection_name=payload.collection_name,
            )
            favorite = await self.favorite_repository.create_favorite(
                user_db_id=user.id,
                collection_id=collection.id,
                poi_id=cleaned["poi_id"],
                name=cleaned["name"],
                address=cleaned.get("address"),
                photo=cleaned.get("photo"),
                location=cleaned.get("location"),
                cuisine_type=cleaned.get("cuisine_type"),
                rating=cleaned.get("rating"),
                avg_price=cleaned.get("avg_price"),
                distance=cleaned.get("distance"),
                recommended_dishes=cleaned.get("recommended_dishes"),
                review_summary=cleaned.get("review_summary"),
                recommend_reason=cleaned.get("recommend_reason"),
                raw_data=cleaned.get("raw_data"),
            )
            await self.db.commit()
            await self.db.refresh(favorite)
            await self._refresh_memory_after_commit(user.user_id)

            return AddFavoriteRestaurantResponse(
                success=True,
                already_exists=False,
                favorite_id=favorite.id,
                message="收藏成功",
            )

        except IntegrityError:
            await self.db.rollback()
            existing_favorite = await self.favorite_repository.get_favorite_by_user_and_poi(
                user_db_id=user.id,
                poi_id=payload.poi_id,
            )
            return AddFavoriteRestaurantResponse(
                success=True,
                already_exists=True,
                favorite_id=existing_favorite.id if existing_favorite else None,
                message="餐厅已收藏",
            )
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise
    
    #获取用户收藏夹内的餐厅
    async def list_favorites(
        self,
        user_id: str,
        collection_id: int | None = None,
    ) -> list[FavoriteRestaurantResponse]:
        user = await self._get_existing_user(user_id)

        if collection_id is not None:
            await self._validate_collection_owner(user, collection_id)

        favorites = await self.favorite_repository.get_favorites_by_user(
            user_db_id=user.id,
            collection_id=collection_id,
        )
        return [self._build_favorite_response(favorite) for favorite in favorites]

    #删除收藏夹内的餐厅
    async def delete_favorite(
        self,
        user_id: str,
        favorite_id: int,
    ) -> DeleteFavoriteResponse:
        try:
            user = await self._get_existing_user(user_id)
            favorite = await self.favorite_repository.get_favorite_by_id(favorite_id)
            if favorite is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="收藏餐厅不存在",
                )
            if favorite.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="收藏餐厅不存在",
                )

            await self.favorite_repository.delete_favorite(favorite)
            await self.db.commit()
            await self._refresh_memory_after_commit(user.user_id)

            return DeleteFavoriteResponse(success=True,message="收藏已删除")

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    #判断用户是否存在
    async def _get_existing_user(self, user_id: str) -> User:
        user = await self.favorite_repository.get_user_by_user_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        return user

    #如果是默认收藏夹则查询用户的默认收藏夹，
    #如果不是默认收藏夹则验证用户与收藏夹之间的关系，如果验证通过则返回收藏夹对象，如果验证不通过则抛出异常
    async def _resolve_collection(
        self,
        user: User,
        collection_id: int | None,
        collection_name: str | None = None,
    ) -> FavoriteCollection:
        normalized_name = collection_name.strip() if collection_name else None
        if normalized_name:
            collection = (
                await self.favorite_repository.get_collection_by_user_and_name(
                    user_db_id=user.id,
                    name=normalized_name,
                )
            )
            if collection is not None:
                return collection
            return await self.favorite_repository.create_collection(
                user_db_id=user.id,
                name=normalized_name,
            )

        if collection_id is None:
            collection = await self.favorite_repository.get_default_collection(user.id)
            if collection is None:
                collection = await self.favorite_repository.create_collection(
                    user_db_id=user.id,
                    name="默认收藏夹",
                    is_default=True,
                )
            return collection

        return await self._validate_collection_owner(user, collection_id)

    #验证用户与收藏夹之间的关系
    async def _validate_collection_owner(
        self,
        user: User,
        collection_id: int,
    ) -> FavoriteCollection:
        collection = await self.favorite_repository.get_collection_by_id(collection_id)
        if collection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="收藏夹不存在",
            )
        if collection.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="收藏夹不属于当前用户",
            )
        return collection

    async def _refresh_memory_after_commit(self, user_id: str) -> None:
        try:
            refresh_response = await MemoryService(self.db).refresh_long_term_memory(
                user_id=user_id
            )
            if not refresh_response.success:
                print(
                    "Warning: Memory refresh failed after favorite change. "
                    f"Message: {refresh_response.message}"
                )
        except Exception as exc:
            print(f"Warning: Memory refresh failed after favorite change: {exc}")

    @staticmethod
    def _update_existing_favorite(
        favorite: FavoriteRestaurant,
        values: dict,
        collection_id: int,
    ) -> bool:
        changed = False
        if favorite.collection_id != collection_id:
            favorite.collection_id = collection_id
            changed = True

        for field in (
            "name",
            "address",
            "photo",
            "location",
            "cuisine_type",
            "rating",
            "avg_price",
            "distance",
            "recommended_dishes",
            "review_summary",
            "recommend_reason",
            "raw_data",
        ):
            value = values.get(field)
            if value is None:
                continue
            if getattr(favorite, field) != value:
                setattr(favorite, field, value)
                changed = True

        return changed


    #构建收藏夹反馈格式
    def _build_collection_response(
        self,
        collection: FavoriteCollection,
        restaurant_count: int,
    ) -> FavoriteCollectionResponse:
        return FavoriteCollectionResponse(
            id=collection.id,
            user_id=collection.user_id,
            name=collection.name,
            description=collection.description,
            is_default=collection.is_default,
            restaurant_count=restaurant_count,
        )

    #构造成schema中的格式
    def _build_favorite_response(
        self,
        favorite: FavoriteRestaurant,
    ) -> FavoriteRestaurantResponse:
        return FavoriteRestaurantResponse(
            id=favorite.id,
            collection_id=favorite.collection_id,
            poi_id=favorite.poi_id,
            name=favorite.name,
            address=favorite.address,
            photo=favorite.photo,
            location=favorite.location,
            cuisine_type=favorite.cuisine_type,
            rating=favorite.rating,
            avg_price=favorite.avg_price,
            distance=favorite.distance,
            recommended_dishes=favorite.recommended_dishes,
            review_summary=favorite.review_summary,
            recommend_reason=favorite.recommend_reason,
            created_at=favorite.created_at,
        )
