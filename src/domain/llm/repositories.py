"""LLM repository interface (domain contract)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from .entities import LLMLogEntry
from .value_objects import LLMRequestType


class LLMLogRepository(ABC):
    """
    Port: Repository interface for LLM API call logs.

    Stores audit trail of all LLM requests/responses for:
    - Monitoring performance
    - Debugging failed requests
    - Cost analysis
    - Compliance/audit
    """

    @abstractmethod
    async def save(self, log_entry: LLMLogEntry) -> None:
        """Record a single LLM API call."""
        pass

    @abstractmethod
    async def get_by_id(self, log_id: UUID) -> Optional[LLMLogEntry]:
        """Retrieve specific log entry by ID."""
        pass

    @abstractmethod
    async def get_user_logs(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> list[LLMLogEntry]:
        """
        Get recent LLM calls made by specific user.

        Useful for: audit trail, user-specific debugging
        """
        pass

    @abstractmethod
    async def get_failed_logs(
        self,
        limit: int = 100,
    ) -> list[LLMLogEntry]:
        """
        Get recent failed LLM requests.

        Useful for: error analysis, monitoring
        """
        pass

    @abstractmethod
    async def get_slow_logs(
        self,
        limit: int = 100,
    ) -> list[LLMLogEntry]:
        """
        Get requests that exceeded latency threshold.

        Useful for: performance monitoring, SLA tracking
        """
        pass

    @abstractmethod
    async def get_logs_by_request_type(
        self,
        request_type: LLMRequestType,
        limit: int = 100,
    ) -> list[LLMLogEntry]:
        """Get logs filtered by request type (fact | chat)."""
        pass

    @abstractmethod
    async def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[LLMLogEntry]:
        """
        Query logs within a date range.

        Useful for: analytics, cost reporting
        """
        pass

    @abstractmethod
    async def list_logs(
        self,
        offset: int = 0,
        limit: int = 100,
        request_type: LLMRequestType | None = None,
        fallback_only: bool = False,
    ) -> list[LLMLogEntry]:
        """Get logs with optional filters and pagination."""
        pass

    @abstractmethod
    async def count_logs(
        self,
        request_type: LLMRequestType | None = None,
        fallback_only: bool = False,
    ) -> int:
        """Count logs with optional filters."""
        pass

    @abstractmethod
    async def get_average_latency(self) -> float | None:
        """Get average latency across logs with a measured duration."""
        pass

    @abstractmethod
    async def get_request_counts_by_type(self) -> dict[LLMRequestType, int]:
        """Aggregate request counts grouped by request type."""
        pass
