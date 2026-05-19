from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field

class ShortTermMemorySetRequest(BaseModel):
    session_id: str
    user_id: str | None = None
    data: dict[str,Any]

class ShortTermMemoryUpdateRequest(BaseModel):
    session_id:str
    patch: dict[str,Any]

class AppendCandidateRequest(BaseModel):
    session_id:str
    restaurant:dict[str,Any]

class ShortTermMemoryResponse(BaseModel):
    session_id:str
    memory:dict[str,Any]

class MemoryOperationResponse(BaseModel):
    success:bool
    message:str
    memory:dict[str,Any] | None = None

class PricePreference(BaseModel):
    min_price:int | None = None
    max_price:int | None = None
    avg_price: float | None = None

class LongTermMemoryData(BaseModel):
    favorite_cuisines:list[str] = Field(default_factory=list)
    taste_preference:list[str] = Field(default_factory=list)
    avoid_foods:list[str] = Field(default_factory=list)
    price_preference:PricePreference = Field(default_factory=PricePreference)
    favorite_dishes:list[str] = Field(default_factory=list)
    preferred_scenes:list[str] = Field(default_factory=list)
    memory_summary:str=""
    source_version:int=1

class LongTermMemoryResponse(BaseModel):
    user_id:str
    memory:LongTermMemoryData
    last_updated:datetime | None = None

class RefreshLongTermMemoryResponse(BaseModel):
    success:bool
    message:str
    memory: LongTermMemoryResponse




