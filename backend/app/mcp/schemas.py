from pydantic import BaseModel, Field

#MCP的返回schemas
class Location(BaseModel):
    longitude: float
    latitude: float


class GeocodeRequest(BaseModel):
    address: str
    city: str | None = None


class GeocodeResponse(BaseModel):
    address: str
    formatted_address: str | None = None
    location: Location | None = None
    raw: dict | None = None


class TextSearchRequest(BaseModel):
    keywords: str
    city: str | None = None
    city_limit: bool | None = None
    limit: int = Field(default=10, ge=1, le=50)


class AroundSearchRequest(BaseModel):
    location: Location
    keywords: str = "美食"
    radius: int = Field(default=3000, ge=1)
    limit: int = Field(default=10, ge=1, le=50)


class PlaceDetailRequest(BaseModel):
    poi_id: str


class RestaurantMCPResult(BaseModel):
    poi_id: str
    name: str
    address: str | None = None
    location: dict | None = None
    distance: float | None = None
    category: str | None = None
    cuisine_type: str | None = None
    rating: float | None = None
    avg_price: int | None = None
    business_hours: str | None = None
    phone: str | None = None
    photo: str | None = None
    review_summary: str | None = None
    recommended_dishes: list | None = None
    raw_data: dict | None = None


class SearchResponse(BaseModel):
    restaurants: list[RestaurantMCPResult]
    raw: dict | None = None


class PlaceDetailResponse(BaseModel):
    restaurant: RestaurantMCPResult
    raw: dict | None = None
