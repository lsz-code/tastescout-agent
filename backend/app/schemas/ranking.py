from typing import Any

from pydantic import BaseModel, ConfigDict, Field

class RankingInputRestaurant(BaseModel):
    poi_id:str
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
    raw_data: dict | None = None


class RankingContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    favorite_cuisines: list[str] = Field(default_factory=list)
    taste_preference: list[str] = Field(default_factory=list)
    avoid_foods: list[str] = Field(default_factory=list)
    price_preference: dict[str, Any] = Field(default_factory=dict)
    favorite_dishes: list[str] = Field(default_factory=list)
    preferred_scenes: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)

class RankingRequest(BaseModel):
    restaurants: list[RankingInputRestaurant] = Field(min_length=1)
    memory: dict[str, Any] | RankingContext | None = None
    filters: dict[str, Any] | None = None
    limit: int = Field(default=10, ge=1, le=50)

class RankedRestaurant(BaseModel):
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
    score: float

class RankingResponse(BaseModel):
    restaurants: list[RankedRestaurant]
