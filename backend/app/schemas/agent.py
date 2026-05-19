from typing import Any

from pydantic import BaseModel, Field

class AgentChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    location: dict[str, Any] | None = None
    location_label: str | None = None


class AgentToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    success: bool = True
    error: str | None = None


class AgentChatResponse(BaseModel):
    user_id: str
    session_id: str
    reply: str
    intent: str | None = None
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
    data: dict[str, Any] | None = None
    memory_used: bool = False
