from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    user_id: str
    session_id: str
    message: str
    location: dict[str, Any] | None
    location_label: str | None
    intent: str | None
    search_slots: dict[str, Any] | None
    missing_slots: list[str]
    planned_tool_args: dict[str, Any]
    short_term_memory: dict[str, Any]
    long_term_memory: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    tool_result: dict[str, Any] | None
    data: dict[str, Any] | None
    reply: str | None
    error: str | None
    memory_used: bool


