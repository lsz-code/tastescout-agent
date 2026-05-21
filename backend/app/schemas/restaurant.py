from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

"""
构造餐厅相关的Pydantic模型，用于API请求和响应的数据验证和序列化。
"""

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


class UpsertRestaurantRequest(BaseModel):
    poi_id: str
    name: str
    address: str | None = None
    photo: str | None = None
    location: dict[str, Any] | str | None = None
    cuisine_type: str | None = None
    rating: float | None = None
    avg_price: int | None = None
    raw_data: dict[str, Any] | None = None


class CreateReviewRequest(BaseModel):
    user_id: str
    content: str
    rating: float | None = Field(default=None, ge=1, le=5)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("评论内容不能为空")
        return content


class ReviewResponse(BaseModel):
    id: int
    restaurant_id: int
    user_id: str
    username: str | None = None
    content: str
    rating: float | None = None
    created_at: datetime
    updated_at: datetime


class RestaurantDetailResponse(BaseModel):
    id: int
    poi_id: str
    name: str
    address: str | None = None
    photo: str | None = None
    location: dict[str, Any] | str | None = None
    cuisine_type: str | None = None
    rating: float | None = None
    avg_price: int | None = None
    raw_data: dict[str, Any] | None = None
    reviews: list[ReviewResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
