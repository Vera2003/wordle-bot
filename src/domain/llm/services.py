"""LLM domain services (cross-entity business logic)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .entities import LLMLogEntry
from .value_objects import (
    LLMRequestType,
    LLMModel,
    LLMPrompt,
    LLMResponse,
    LLMLatency,
)
from .errors import LLMResponseError, LLMLatencyError


class LLMService:
    """
    Domain service: LLM business logic.
    
    Main responsibilities:
    - Validate LLM requests
    - Create log entries
    - Analyze logs for issues
    """
    
    # Performance thresholds
    ACCEPTABLE_LATENCY_MS = 3000
    WARNING_LATENCY_MS = 2000
    
    @staticmethod
    def create_log_entry(
        request_type: LLMRequestType,
        model: LLMModel,
        prompt: LLMPrompt,
        response: LLMResponse,
        latency_ms: Optional[int],
        user_id: Optional[UUID] = None,
        error: Optional[str] = None,
    ) -> LLMLogEntry:
        """
        Create a log entry for an LLM API call.
        
        What happens here:
        - Construct structured log record
        - Generate UUID placeholder for DB
        - Capture all context for audit trail
        
        Args:
            request_type: Type of request (fact | chat)
            model: Which model was called
            prompt: The prompt sent
            response: The response received (or None if error)
            latency_ms: Response time in milliseconds
            user_id: Which user made the request (optional)
            error: Error message if request failed
        
        Returns: LLMLogEntry ready for repository save
        """
        latency = LLMLatency(latency_ms)
        
        log_entry = LLMLogEntry(
            id=uuid4(),
            request_type=request_type,
            model=model,
            prompt=prompt,
            response=response,
            latency=latency,
            user_id=user_id,
            error=error,
            created_at=datetime.now(),
        )
        
        return log_entry
    
    @staticmethod
    def validate_latency(latency_ms: Optional[int]) -> None:
        """
        Check if response time is acceptable.
        
        What happens here:
        - Log warning if latency high but acceptable
        - Raise exception if unacceptable
        
        Args:
            latency_ms: Response time in milliseconds
        
        Raises: LLMLatencyError if latency exceeds threshold
        """
        if latency_ms is None:
            return  # Unknown latency, no validation
        
        if latency_ms > LLMService.ACCEPTABLE_LATENCY_MS:
            raise LLMLatencyError(
                f"LLM latency {latency_ms}ms exceeds acceptable "
                f"threshold of {LLMService.ACCEPTABLE_LATENCY_MS}ms"
            )
    
    @staticmethod
    def log_requires_investigation(log_entry: LLMLogEntry) -> bool:
        """
        Check if this log entry indicates a problem needing attention.
        
        What happens here:
        - Flag errors
        - Flag slow responses
        - Flag fallback responses
        
        Useful for: alerting, metrics, debugging
        """
        return (
            log_entry.is_error
            or log_entry.is_slow_response()
            or log_entry.response.is_fallback
        )
