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
