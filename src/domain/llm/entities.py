"""LLM domain entities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from .value_objects import (
    LLMRequestType,
    LLMModel,
    LLMPrompt,
    LLMResponse,
    LLMLatency,
)
from .errors import LLMResponseError, LLMLatencyError


class LLMLogEntry:
    """
    Entity: A single LLM API call record.
    
    Records what was sent, what was received, and any errors.
    Used for:
    - Monitoring API performance
    - Auditing prompt quality
    - Debugging failed requests
    - Cost tracking
    """
    
    def __init__(
        self,
        id: UUID,
        request_type: LLMRequestType,
        model: LLMModel,
        prompt: LLMPrompt,
        response: LLMResponse,
        latency: LLMLatency,
        user_id: Optional[UUID] = None,
        error: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self._id = id
        self._request_type = request_type
        self._model = model
        self._prompt = prompt
        self._response = response
        self._latency = latency
        self._user_id = user_id
        self._error = error
        self._created_at = created_at or datetime.now()
    
    @property
    def id(self) -> UUID:
        return self._id
    
    @property
    def request_type(self) -> LLMRequestType:
        return self._request_type
    
    @property
    def model(self) -> LLMModel:
        return self._model
    
    @property
    def prompt(self) -> LLMPrompt:
        return self._prompt
    
    @property
    def response(self) -> LLMResponse:
        return self._response
    
    @property
    def latency(self) -> LLMLatency:
        return self._latency
    
    @property
    def user_id(self) -> Optional[UUID]:
        """User who made the request (None for system/admin requests)."""
        return self._user_id
    
    @property
    def error(self) -> Optional[str]:
        """Error message if request failed."""
        return self._error
    
    @property
    def created_at(self) -> datetime:
        return self._created_at
    
    @property
    def is_successful(self) -> bool:
        """Request succeeded (got response, no error)."""
        return self._response.is_successful and self._error is None
    
    @property
    def is_error(self) -> bool:
        """Request failed with error."""
        return self._error is not None
    
    def is_slow_response(self) -> bool:
        """Response was slower than acceptable threshold."""
        return self._latency.is_slow()
    
    def __repr__(self) -> str:
        status = "ok" if self.is_successful else "error" if self.is_error else "fallback"
        return (
            f"LLMLogEntry(id={self._id}, type={self._request_type.value}, "
            f"status={status}, latency={self._latency.milliseconds}ms)"
        )
