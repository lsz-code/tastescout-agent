from pydantic import BaseModel


class UserBootstrapRequest(BaseModel):
    user_id: str
    username: str | None = None
    avatar_url: str | None = None


class UserBootstrapResponse(BaseModel):
    user_id: str
    username: str | None
    default_collection_id: int
    memory_initialized: bool
    is_new_user: bool
