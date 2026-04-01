"""LLM application DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from ..common.dto import BaseDTO


class LLMCompletionOutput(BaseDTO):
    """Low-level completion result returned by the generation port."""

    text: str = Field(...)
    is_fallback: bool = Field(...)
    latency_ms: int = Field(..., ge=0)


class GeneFactOutput(BaseDTO):
    """Fact generation response DTO."""

    gene_name: str = Field(...)
    fact: str = Field(...)
    is_fallback: bool = Field(...)
    latency_ms: int = Field(..., ge=0)


class ChatAnswerOutput(BaseDTO):
    """Chat response DTO."""

    question: str = Field(...)
    answer: str = Field(...)
    is_fallback: bool = Field(...)
    latency_ms: int = Field(..., ge=0)


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


class LLMLogListOutput(BaseDTO):
    """Paginated llm log list DTO."""

    total: int = Field(..., ge=0)
    items: list[LLMLogOutput] = Field(default_factory=list)


class LLMStatsOutput(BaseDTO):
    """Aggregated llm monitoring stats."""

    total_requests: int = Field(..., ge=0)
    fallback_count: int = Field(..., ge=0)
    fallback_rate: float = Field(..., ge=0)
    avg_latency_ms: float | None = Field(None, ge=0)
    requests_by_type: dict[str, int] = Field(default_factory=dict)
