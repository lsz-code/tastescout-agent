from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status

from app.models.favorite_collection import FavoriteCollection
from app.models.favorite_restaurant import FavoriteRestaurant
from app.models.user import User
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
            
            #判断餐厅是否存在
            existing_favorite = (
                await self.favorite_repository.get_favorite_by_user_and_poi(
                    user_db_id=user.id,
                    poi_id=payload.poi_id,
                )
            )
            if existing_favorite is not None:
                return AddFavoriteRestaurantResponse(
                    success=True,
                    already_exists=True,
                    favorite_id=existing_favorite.id,
                    message="餐厅已收藏",
                )

            collection = await self._resolve_collection(user, payload.collection_id)
            favorite = await self.favorite_repository.create_favorite(
                user_db_id=user.id,
                collection_id=collection.id,
                poi_id=payload.poi_id,
                name=payload.name,
                address=payload.address,
                photo=payload.photo,
                location=payload.location,
                cuisine_type=payload.cuisine_type,
                rating=payload.rating,
                avg_price=payload.avg_price,
                distance=payload.distance,
                recommended_dishes=payload.recommended_dishes,
                review_summary=payload.review_summary,
                recommend_reason=payload.recommend_reason,
                raw_data=payload.raw_data,
            )
            #if we want to trigger memory refresh after favorite changes, 
            # we can do it here.
            # But we can't make the error of resfresh action affect the favorite adding process, 
            # so we should make a separate async function for that.
            #这里先触发修改长期记忆的函数，但不等待它完成，也不让它的错误影响收藏添加的流程
            await self._on_favorite_changed(user)
            await self.db.commit()
            #这里要等数据库提交成功后再刷新对象
            await self.db.refresh(favorite)

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
            await self._on_favorite_changed(user)
            await self.db.commit()

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
    ) -> FavoriteCollection:
        if collection_id is None:
            collection = await self.favorite_repository.get_default_collection(user.id)
            if collection is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="默认收藏夹不存在",
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

    #通用工具函数，当收藏夹发生变化时，触发记忆更新
    async def _on_favorite_changed(self, user: User) -> None:
        # TODO: Trigger Memory Refresh after favorite changes.
        return None

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
            cuisine_type=favorite.cuisine_type,
            rating=favorite.rating,
            avg_price=favorite.avg_price,
            distance=favorite.distance,
            recommended_dishes=favorite.recommended_dishes,
            review_summary=favorite.review_summary,
            recommend_reason=favorite.recommend_reason,
            created_at=favorite.created_at,
        )
