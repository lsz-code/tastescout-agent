from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.schemas import (
    AroundSearchRequest as MCPAroundSearchRequest,
    GeocodeRequest,
    Location as MCPLocation,
    PlaceDetailRequest,
    TextSearchRequest,
)
from app.memory.short_term import ShortTermMemory, get_short_term_memory
from app.schemas.memory import LongTermMemoryData
from app.schemas.restaurant import (
    Location,
    RestaurantSearchItem,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)
from app.services.mcp_service import MCPService
from app.services.memory_service import MemoryService
from app.services.ranking_service import RankingService
from app.utils.geo import calculate_distance_meters


class RestaurantSearchService:
    DETAIL_FIELDS = [
        "rating",
        "avg_price",
        "location",
        "category",
        "cuisine_type",
        "business_hours",
        "photo",
        "address",
    ]

    def __init__(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory | None = None,
    ) -> None:
        self.db = db
        self.memory_service = MemoryService(db)
        self.mcp_service = MCPService()
        self.ranking_service = RankingService()
        self.short_term_memory = short_term_memory or get_short_term_memory()

    #餐厅搜索主方法，根据用户输入的搜索条件和用户的长期记忆进行餐厅搜索、过滤和排序，并将搜索结果写入短期记忆供后续推荐使用。
    async def search(
        self,
        payload: RestaurantSearchRequest,
    ) -> RestaurantSearchResponse:
        memory_response = await self.memory_service.get_long_term_memory(payload.user_id)
        long_term_memory = memory_response.memory or LongTermMemoryData()
        memory_used = self._has_memory(long_term_memory)

        session_memory = await self._get_session_memory(payload.session_id)

        #获取餐厅唯一ID
        recommended_poi_ids = self._as_str_list(
            session_memory.get("recommended_poi_ids")
        )
        search_location = await self._resolve_location(payload)

        restaurants = await self._search_restaurants(payload, search_location)
        restaurants = self._dedupe_by_poi_id(restaurants)

        #收集餐厅详情
        restaurants = await self._enhance_restaurant_details(
            restaurants=restaurants,
            user_location=search_location,
        )

        #过滤餐厅
        restaurants = self._filter_recommended_restaurants(
            restaurants=restaurants,
            recommended_poi_ids=set(recommended_poi_ids),
        )

        #根据用户的长期记忆和搜索条件对餐厅进行排序
        ranked = self.ranking_service.rank_restaurants(
            restaurants=restaurants,
            memory=long_term_memory,
            filters=self._build_ranking_filters(payload),
            limit=payload.limit,
        )

        #格式化餐厅数据
        items = [RestaurantSearchItem(**restaurant) for restaurant in ranked]

        #将数据加入短期记忆，供后续推荐使用
        await self._write_short_term_memory(
            payload=payload,
            location=search_location,
            restaurants=items,
            existing_recommended_poi_ids=recommended_poi_ids,
        )

        return RestaurantSearchResponse(
            user_id=payload.user_id,
            session_id=payload.session_id,
            address=payload.address,
            location=Location(**search_location) if search_location else None,
            keyword=payload.keyword,
            restaurants=items,
            memory_used=memory_used,
            message=self._build_message(items),
        )

    #根据经纬度或地址解析出搜索位置的经纬度坐标
    async def _resolve_location(
        self,
        payload: RestaurantSearchRequest,
    ) -> dict[str, float] | None:
        if payload.location is not None:
            return payload.location.model_dump()

        if not payload.address:
            return None

        #MCP服务，根据地址解析出经纬度坐标
        geocode_result = await self.mcp_service.geocode(
            GeocodeRequest(
                address=payload.address,
                city=payload.city,
            )
        )
        if geocode_result.location is None:
            return None

        return geocode_result.location.model_dump()
    
    #如果有经纬度，则根据经纬度搜索餐厅，如果没有经纬度，则根据地址和关键词搜索餐厅
    async def _search_restaurants(
        self,
        payload: RestaurantSearchRequest,
        location: dict[str, float] | None,
    ) -> list[dict[str, Any]]:
        fetch_limit = max(payload.limit * 5, payload.limit)

        if location is not None:
            #MCP服务，根据经纬度搜索餐厅
            response = await self.mcp_service.around_search(
                MCPAroundSearchRequest(
                    location=MCPLocation(**location),
                    keywords=payload.keyword,
                    radius=payload.radius,
                    limit=fetch_limit,
                )
            )
        else:
            #MCP服务，根据地址和关键词搜索餐厅
            response = await self.mcp_service.text_search(
                TextSearchRequest(
                    keywords=payload.keyword,
                    city=payload.city,
                    limit=fetch_limit,
                )
            )

        return [restaurant.model_dump() for restaurant in response.restaurants]
    
    #通过会话获取短期记忆
    async def _get_session_memory(self, session_id: str | None) -> dict[str, Any]:
        if not session_id:
            return {}
        return await self.short_term_memory.get(session_id)

    #调用MCP工具获取详情，使用_with_calculated_distance方法计算距离
    async def _enhance_restaurant_details(
        self,
        restaurants: list[dict[str, Any]],
        user_location: dict[str, float] | None,
    ) -> list[dict[str, Any]]:
        enhanced: list[dict[str, Any]] = []

        for restaurant in restaurants:
            poi_id = restaurant.get("poi_id")
            if not poi_id:
                enhanced.append(self._with_calculated_distance(restaurant, user_location))
                continue

            try:
                #MCP服务，根据餐厅唯一ID获取餐厅详情
                detail_response = await self.mcp_service.place_detail(
                    PlaceDetailRequest(poi_id=poi_id)
                )
            except Exception:
                enhanced.append(self._with_calculated_distance(restaurant, user_location))
                continue

            detail = detail_response.restaurant.model_dump()
            merged = self._merge_detail(restaurant, detail)
            enhanced.append(self._with_calculated_distance(merged, user_location))

        return enhanced
    #合并信息
    def _merge_detail(
        self,
        restaurant: dict[str, Any],
        detail: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(restaurant)
        for field in self.DETAIL_FIELDS:
            value = detail.get(field)
            if value is not None and value != "":
                merged[field] = value

        raw_data = dict(restaurant.get("raw_data") or {})
        detail_raw_data = detail.get("raw_data")
        if isinstance(detail_raw_data, dict):
            raw_data.update(detail_raw_data)
        if raw_data:
            merged["raw_data"] = raw_data

        if not self._has_distance(merged) and self._has_distance(detail):
            merged["distance"] = detail.get("distance")

        return merged

    #距离计算
    def _with_calculated_distance(
        self,
        restaurant: dict[str, Any],
        user_location: dict[str, float] | None,
    ) -> dict[str, Any]:
        if self._has_distance(restaurant):
            return restaurant

        updated = dict(restaurant)
        distance = calculate_distance_meters(
            user_location,
            restaurant.get("location"),
        )
        if distance is None:
            updated["distance"] = None
            return updated

        updated["distance"] = distance
        return updated

    #根据餐厅id去重餐厅列表，内部去重
    @staticmethod
    def _dedupe_by_poi_id(restaurants: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []

        for restaurant in restaurants:
            poi_id = restaurant.get("poi_id")
            if not poi_id:
                deduped.append(restaurant)
                continue

            poi_id_text = str(poi_id)
            if poi_id_text in seen:
                continue

            seen.add(poi_id_text)
            deduped.append(restaurant)

        return deduped
    
    #推荐餐厅去重，根据推荐历史去重
    @staticmethod
    def _filter_recommended_restaurants(
        restaurants: list[dict[str, Any]],
        recommended_poi_ids: set[str],
    ) -> list[dict[str, Any]]:
        if not recommended_poi_ids:
            return restaurants

        return [
            restaurant
            for restaurant in restaurants
            if str(restaurant.get("poi_id") or "") not in recommended_poi_ids
        ]

    #判断是否具有距离信息
    @staticmethod
    def _has_distance(restaurant: dict[str, Any]) -> bool:
        distance = restaurant.get("distance")
        if distance is None or distance == "":
            return False
        try:
            float(distance)
        except (TypeError, ValueError):
            return False
        return True

    #构建排序过滤条件
    @staticmethod
    def _build_ranking_filters(payload: RestaurantSearchRequest) -> dict[str, Any]:
        filters = payload.filters.model_dump() if payload.filters else {}
        filters["keyword"] = payload.keyword
        return filters

    #写入短期记忆
    async def _write_short_term_memory(
        self,
        payload: RestaurantSearchRequest,
        location: dict[str, float] | None,
        restaurants: list[RestaurantSearchItem],
        existing_recommended_poi_ids: list[str],
    ) -> None:
        candidates = [
            {
                "rank": item.rank,
                "poi_id": item.poi_id,
                "name": item.name,
                "photo": item.photo,
                "address": item.address,
                "cuisine_type": item.cuisine_type,
                "rating": item.rating,
                "avg_price": item.avg_price,
                "distance": item.distance,
                "score": item.score,
                "match_reasons": item.match_reasons,
                "recommend_reason": item.recommend_reason,
            }
            for item in restaurants
        ]
        current_poi_ids = [
            item.poi_id
            for item in restaurants
            if item.poi_id
        ]
        recommended_poi_ids = self._merge_poi_ids(
            existing_recommended_poi_ids=existing_recommended_poi_ids,
            current_poi_ids=current_poi_ids,
        )
        await self.short_term_memory.update(
            payload.session_id,
            {
                "user_id": payload.user_id,
                "current_address": payload.address,
                "current_location": location,
                "current_search_keyword": payload.keyword,
                "current_candidates": candidates,
                "recommended_poi_ids": recommended_poi_ids,
                "last_search_context": {
                    "address": payload.address,
                    "location": location,
                    "keyword": payload.keyword,
                    "city": payload.city,
                    "radius": payload.radius,
                    "limit": payload.limit,
                    "filters": payload.filters.model_dump() if payload.filters else {},
                },
                "last_intent": "search_food",
            },
        )

    #将值转换为字符串列表
    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item]

    #合并推荐餐厅id列表，去重
    @staticmethod
    def _merge_poi_ids(
        existing_recommended_poi_ids: list[str],
        current_poi_ids: list[str],
    ) -> list[str]:
        merged = list(existing_recommended_poi_ids)
        seen = set(existing_recommended_poi_ids)
        for poi_id in current_poi_ids:
            poi_id_text = str(poi_id)
            if poi_id_text not in seen:
                seen.add(poi_id_text)
                merged.append(poi_id_text)
        return merged

    #判断长期记忆中是否有相关信息
    @staticmethod
    def _has_memory(memory: LongTermMemoryData) -> bool:
        return bool(
            memory.favorite_cuisines
            or memory.taste_preference
            or memory.avoid_foods
            or memory.favorite_dishes
            or memory.preferred_scenes
            or memory.price_preference.min_price is not None
            or memory.price_preference.max_price is not None
        )

    #根据餐厅数量构建返回给用户的消息
    @staticmethod
    def _build_message(restaurants: list[RestaurantSearchItem]) -> str:
        if not restaurants:
            return "这附近暂时没有更多新的推荐了，可以换个关键词或扩大搜索范围。"
        return f"为你找到 {len(restaurants)} 家餐厅"
