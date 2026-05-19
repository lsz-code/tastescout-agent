from pydantic import BaseModel,Field

class Location(BaseModel):
    longitude:float
    latitude:float


class RestaurantSearchFilters(BaseModel):
    cuisine:str | None = None
    max_price:int | None = None
    min_rating:float | None = None
    scene: str | None = None

class RestaurantSearchRequest(BaseModel):
    user_id:str
    session_id:str
    address:str|None = None
    location:Location|None = None 
    keyword: str = "美食"
    city: str | None = None
    radius: int = 3000
    limit: int = Field(default=10, ge=1, le=50)
    filters: RestaurantSearchFilters | None = None


class RestaurantSearchItem(BaseModel):
    rank: int
    poi_id: str
    name: str
    address: str | None = None
    photo: str | None = None
    location: dict | None = None
    distance: float | None = None
    cuisine_type: str | None = None
    category: str | None = None
    rating: float | None = None
    avg_price: int | None = None
    recommended_dishes: list | None = None
    review_summary: str | None = None
    recommend_reason: str | None = None
    match_reasons: list[str] = Field(default_factory=list)
    score: float | None = None


class RestaurantSearchResponse(BaseModel):
    user_id: str
    session_id: str
    address: str | None = None
    location: Location | None = None
    keyword: str
    restaurants: list[RestaurantSearchItem]
    memory_used: bool
    message: str