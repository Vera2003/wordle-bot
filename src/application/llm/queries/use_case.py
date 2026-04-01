"""LLM query handlers."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.llm.dto import LLMLogListOutput, LLMLogOutput, LLMStatsOutput
from src.domain.llm import LLMLogEntry, LLMLogRepository, LLMRequestType, LLMService


def _to_log_output(log_entry: LLMLogEntry) -> LLMLogOutput:
    return LLMLogOutput(
        id=log_entry.id,
        user_id=log_entry.user_id,
        request_type=log_entry.request_type.value,
        model=log_entry.model.value,
        prompt=log_entry.prompt.text,
        response=log_entry.response.text,
        is_fallback=log_entry.response.is_fallback,
        latency_ms=log_entry.latency.milliseconds,
        error=log_entry.error,
        created_at=log_entry.created_at,
        requires_investigation=LLMService.log_requires_investigation(log_entry),
    )


class GetLLMLogByIdQuery(BaseModel):
    """Query to fetch one LLM log entry."""

    model_config = ConfigDict(extra="forbid")

    log_id: UUID


class GetLLMLogByIdHandler:
    """Handler for GetLLMLogById query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetLLMLogByIdQuery) -> LLMLogOutput | None:
        log_entry = await self.llm_log_repository.get_by_id(query.log_id)
        if log_entry is None:
            return None
        return _to_log_output(log_entry)


class GetUserLLMLogsQuery(BaseModel):
    """Query to fetch recent LLM logs for a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    limit: int = Field(default=100, ge=1, le=500)


class GetUserLLMLogsHandler:
    """Handler for GetUserLLMLogs query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetUserLLMLogsQuery) -> list[LLMLogOutput]:
        logs = await self.llm_log_repository.get_user_logs(query.user_id, query.limit)
        return [_to_log_output(log_entry) for log_entry in logs]


class GetFailedLLMLogsQuery(BaseModel):
    """Query to fetch recent failed LLM logs."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=500)


class GetFailedLLMLogsHandler:
    """Handler for GetFailedLLMLogs query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetFailedLLMLogsQuery) -> list[LLMLogOutput]:
        logs = await self.llm_log_repository.get_failed_logs(query.limit)
        return [_to_log_output(log_entry) for log_entry in logs]


class GetSlowLLMLogsQuery(BaseModel):
    """Query to fetch slow LLM logs."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=500)


class GetSlowLLMLogsHandler:
    """Handler for GetSlowLLMLogs query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetSlowLLMLogsQuery) -> list[LLMLogOutput]:
        logs = await self.llm_log_repository.get_slow_logs(query.limit)
        return [_to_log_output(log_entry) for log_entry in logs]


class GetLLMLogsByRequestTypeQuery(BaseModel):
    """Query to fetch LLM logs by request type."""

    model_config = ConfigDict(extra="forbid")

    request_type: LLMRequestType
    limit: int = Field(default=100, ge=1, le=500)


class GetLLMLogsByRequestTypeHandler:
    """Handler for GetLLMLogsByRequestType query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetLLMLogsByRequestTypeQuery) -> list[LLMLogOutput]:
        logs = await self.llm_log_repository.get_logs_by_request_type(
            query.request_type,
            query.limit,
        )
        return [_to_log_output(log_entry) for log_entry in logs]


class GetLLMLogsByDateRangeQuery(BaseModel):
    """Query to fetch LLM logs inside a date range."""

    model_config = ConfigDict(extra="forbid")

    start_date: datetime
    end_date: datetime


class GetLLMLogsByDateRangeHandler:
    """Handler for GetLLMLogsByDateRange query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetLLMLogsByDateRangeQuery) -> list[LLMLogOutput]:
        logs = await self.llm_log_repository.get_logs_by_date_range(
            query.start_date,
            query.end_date,
        )
        return [_to_log_output(log_entry) for log_entry in logs]


class GetLLMLogsQuery(BaseModel):
    """Query to fetch llm logs with filters and pagination."""

    model_config = ConfigDict(extra="forbid")

    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)
    request_type: LLMRequestType | None = None
    fallback_only: bool = False


class GetLLMLogsHandler:
    """Handler for filtered llm log list query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetLLMLogsQuery) -> LLMLogListOutput:
        total = await self.llm_log_repository.count_logs(
            request_type=query.request_type,
            fallback_only=query.fallback_only,
        )
        logs = await self.llm_log_repository.list_logs(
            offset=query.skip,
            limit=query.limit,
            request_type=query.request_type,
            fallback_only=query.fallback_only,
        )
        return LLMLogListOutput(
            total=total,
            items=[_to_log_output(log_entry) for log_entry in logs],
        )


class GetLLMStatsQuery(BaseModel):
    """Query to fetch aggregated llm monitoring stats."""

    model_config = ConfigDict(extra="forbid")


class GetLLMStatsHandler:
    """Handler for llm stats query."""

    def __init__(self, llm_log_repository: LLMLogRepository):
        self.llm_log_repository = llm_log_repository

    async def __call__(self, query: GetLLMStatsQuery) -> LLMStatsOutput:
        del query
        total = await self.llm_log_repository.count_logs()
        fallback_count = await self.llm_log_repository.count_logs(fallback_only=True)
        avg_latency = await self.llm_log_repository.get_average_latency()
        counts = await self.llm_log_repository.get_request_counts_by_type()

        return LLMStatsOutput(
            total_requests=total,
            fallback_count=fallback_count,
            fallback_rate=round(fallback_count / total * 100, 2) if total else 0.0,
            avg_latency_ms=round(float(avg_latency), 1) if avg_latency is not None else None,
            requests_by_type={request_type.value: count for request_type, count in counts.items()},
        )
