from typing import Any

from app.core.config import settings
from app.guardrails.mcp_result_guard import MCPResultGuard
from app.mcp.amap_proxy_client import AmapProxyClient
from app.mcp.schemas import (
    AroundSearchRequest,
    GeocodeRequest,
    GeocodeResponse,
    Location,
    PlaceDetailRequest,
    PlaceDetailResponse,
    RestaurantMCPResult,
    SearchResponse,
    TextSearchRequest,
)

#MCP服务类，这里MCP工具实际的调用我们是运行在另一个进程中的，
#因为存在包冲突，以及考虑到未来可能接入其他地图服务商的MCP工具，所以我们通过HTTP接口来调用MCP工具，
#MCPservice层负责适配工具接口和我们内部的调用方式，以及对工具返回的数据进行标准化处理，适配我们内部的格式
class MCPService:
    def __init__(self) -> None:
        self.client = AmapProxyClient(
            proxy_url=settings.AMAP_MCP_PROXY_URL,
            timeout_seconds=settings.MCP_TIMEOUT_SECONDS,
        )

    #列出工具列表
    async def list_tools(self) -> list[dict[str, Any]]:
        return await self.client.list_tools()

    #根据地址解析出经纬度坐标
    async def geocode(self, request: GeocodeRequest) -> GeocodeResponse:
        raw = await self.client.geocode(
            address=request.address,
            city=request.city,
        )
        geocode = self._first_item(raw, "results") or {}
        #这里的位置是经纬度
        location = self._parse_location(geocode.get("location"))

        formatted_address = geocode.get("formatted_address")
        if formatted_address is None:
            formatted_address = self._build_formatted_address(geocode)

        return GeocodeResponse(
            address=request.address,
            formatted_address=formatted_address,
            location=Location(**location) if location else None,
            raw=raw,
        )

    #根据地址和关键词搜索餐厅
    async def text_search(self, request: TextSearchRequest) -> SearchResponse:
        raw = await self.client.text_search(
            keywords=request.keywords,
            city=request.city,
        )
        restaurants = [
            RestaurantMCPResult(**self._normalize_poi(poi))
            for poi in self._extract_pois(raw)[: request.limit]
        ]
        return SearchResponse(restaurants=restaurants, raw=raw)

    #MCP，根据经纬度搜索餐厅
    async def around_search(self, request: AroundSearchRequest) -> SearchResponse:
        raw = await self.client.around_search(
            location=request.location.model_dump(),
            keywords=request.keywords,
            radius=request.radius,
        )
        restaurants = [
            RestaurantMCPResult(**self._normalize_poi(poi))
            for poi in self._extract_pois(raw)[: request.limit]
        ]
        return SearchResponse(restaurants=restaurants, raw=raw)

    #MCP，根据餐厅唯一ID获取餐厅详情
    async def place_detail(
        self,
        request: PlaceDetailRequest,
    ) -> PlaceDetailResponse:
        raw = await self.client.place_detail(request.poi_id)
        poi = (
            self._first_item(raw, "pois")
            or self._first_item(raw, "results")
            or self._first_item(raw, "data")
            or raw
        )

        return PlaceDetailResponse(
            restaurant=RestaurantMCPResult(**self._normalize_poi(poi)),
            raw=raw,
        )

    #位置信息标准化，适配不同接口返回的格式差异
    def _normalize_poi(self, poi: dict[str, Any]) -> dict[str, Any]:
        category = poi.get("type") or poi.get("typecode")

        normalized = {
            "poi_id": poi.get("id"),
            "name": poi.get("name"),
            "address": poi.get("address"),
            "location": self._parse_location(poi.get("location")),
            "distance": poi.get("distance"),
            "category": category,
            "cuisine_type": self._infer_cuisine_type(poi),
            "rating": poi.get("rating"),
            "avg_price": poi.get("cost"),
            "business_hours": poi.get("open_time") or poi.get("opentime2"),
            "phone": poi.get("tel"),
            "photo": poi.get("photo"),
            "review_summary": None,
            "recommended_dishes": None,
            "raw_data": poi,
        }

        return MCPResultGuard.validate_restaurant(normalized)

    #推断菜系
    def _infer_cuisine_type(self, poi: dict[str, Any]) -> str | None:
        category = poi.get("type") or poi.get("typecode")
        typecode = str(poi.get("typecode") or "")
        text = " ".join(
            str(value)
            for value in [
                poi.get("type"),
                poi.get("name"),
                poi.get("address"),
                poi.get("business_area"),
            ]
            if value
        )

        if any(keyword in text for keyword in ["四川菜", "川菜", "川"]):
            return "川菜"
        if "火锅" in text:
            return "火锅"
        if "烤鱼" in text:
            return "烤鱼"
        if "烧烤" in text:
            return "烧烤"
        if any(keyword in text for keyword in ["日本料理", "日料", "日本"]):
            return "日料"
        if "050102" in typecode:
            return "川菜"
        if "050117" in typecode:
            return "火锅"
        if "050100" in typecode:
            return "中餐"

        return str(category) if category else None

    #提取餐厅列表，适配不同接口返回的格式差异
    @staticmethod
    def _extract_pois(payload: dict[str, Any]) -> list[dict[str, Any]]:
        if payload.get("id") and payload.get("name"):
            return [payload]

        for key in ["pois", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [poi for poi in value if isinstance(poi, dict)]

        data = payload.get("data")
        if isinstance(data, list):
            return [poi for poi in data if isinstance(poi, dict)]
        if isinstance(data, dict):
            if data.get("id") and data.get("name"):
                return [data]
            for key in ["pois", "results"]:
                value = data.get(key)
                if isinstance(value, list):
                    return [poi for poi in value if isinstance(poi, dict)]

        return []

    #适配不同接口返回的格式差异，获取第一个字典类型的值
    @staticmethod
    def _first_item(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value[0]

        data = payload.get("data")
        if isinstance(data, dict):
            nested = data.get(key)
            if isinstance(nested, dict):
                return nested
            if isinstance(nested, list) and nested and isinstance(nested[0], dict):
                return nested[0]

        return None

    #解析位置信息，适配不同接口返回的格式差异
    @staticmethod
    def _parse_location(value: Any) -> dict[str, float] | None:
        if isinstance(value, dict):
            longitude = value.get("longitude")
            latitude = value.get("latitude")
            if longitude is None or latitude is None:
                return None
            return {"longitude": float(longitude), "latitude": float(latitude)}

        if not isinstance(value, str) or "," not in value:
            return None

        longitude, latitude = value.split(",", maxsplit=1)
        return {"longitude": float(longitude), "latitude": float(latitude)}

    #构建格式化地址，适配不同接口返回的格式差异
    @staticmethod
    def _build_formatted_address(geocode: dict[str, Any]) -> str | None:
        parts = [
            geocode.get("province"),
            geocode.get("city"),
            geocode.get("district"),
        ]
        formatted = "".join(str(part) for part in parts if part)
        return formatted or None
