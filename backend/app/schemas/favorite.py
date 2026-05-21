from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CreateFavoriteCollectionRequest(BaseModel):
    user_id: str
    name: str
    description: str | None = None


class FavoriteCollectionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    is_default: bool
    restaurant_count: int


class AddFavoriteRestaurantRequest(BaseModel):
    user_id: str
    collection_id: int | None = None
    collection_name: str | None = None
    poi_id: str
    name: str
    address: str | None = None
    photo: str | None = None
    location: dict[str, Any] | None = None
    cuisine_type: str | None = None
    rating: float | None = None
    avg_price: int | None = None
    distance: float | None = None
    recommended_dishes: list[Any] | dict[str, Any] | None = None
    review_summary: str | None = None
    recommend_reason: str | None = None
    raw_data: dict[str, Any] | None = None


class AddFavoriteRestaurantResponse(BaseModel):
    success: bool
    already_exists: bool
    favorite_id: int | None
    message: str


class FavoriteRestaurantResponse(BaseModel):
    id: int
    collection_id: int
    poi_id: str
    name: str
    address: str | None
    photo: str | None = None
    cuisine_type: str | None
    rating: float | None
    avg_price: int | None
    distance: float | None
    recommended_dishes: Any
    review_summary: str | None
    recommend_reason: str | None
    created_at: datetime


class DeleteFavoriteResponse(BaseModel):
    success: bool
    message: str | None
