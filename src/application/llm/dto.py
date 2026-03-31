"""LLM application DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from ..common.dto import BaseDTO


class LLMLogOutput(BaseDTO):
    """Read DTO for an LLM log entry."""

    id: UUID = Field(...)
    user_id: UUID | None = Field(None)
    request_type: str = Field(...)
    model: str = Field(...)
    prompt: str = Field(...)
    response: str | None = Field(None)
    is_fallback: bool = Field(...)
    latency_ms: int | None = Field(None, ge=0)
    error: str | None = Field(None)
    created_at: datetime = Field(...)
    requires_investigation: bool = Field(...)
