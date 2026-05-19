from typing import Any

from pydantic import BaseModel, Field


class GuardrailValidateRequest(BaseModel):
    data: dict[str, Any]
    guard_type: str = "database_write"


class GuardrailValidateResponse(BaseModel):
    valid: bool
    cleaned_data: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
