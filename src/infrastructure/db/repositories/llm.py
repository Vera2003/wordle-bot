"""LLM log repository implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.llm import LLMLogEntry, LLMLogRepository, LLMRequestType
from src.infrastructure.db.mappers.llm import LLMLogMapper
from src.infrastructure.db.models.llm import LLMLogModel


class LLMLogRepositoryImpl(LLMLogRepository):
    """SQLAlchemy implementation of LLMLogRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, log_entry: LLMLogEntry) -> None:
        existing = await self.session.get(LLMLogModel, log_entry.id)
        if existing:
            existing.user_id = log_entry.user_id
            existing.request_type = log_entry.request_type.value
            existing.model = log_entry.model.value
            existing.prompt = log_entry.prompt.text
            existing.response = log_entry.response.text
            existing.is_fallback = log_entry.response.is_fallback
            existing.latency_ms = log_entry.latency.milliseconds
            existing.error = log_entry.error
            existing.created_at = log_entry.created_at
        else:
            self.session.add(LLMLogMapper.domain_to_model(log_entry))
        await self.session.flush()

    async def get_by_id(self, log_id: UUID) -> Optional[LLMLogEntry]:
        model = await self.session.get(LLMLogModel, log_id)
        return LLMLogMapper.model_to_domain(model) if model else None

    async def get_user_logs(self, user_id: UUID, limit: int = 100) -> list[LLMLogEntry]:
        result = await self.session.execute(
            select(LLMLogModel)
            .where(LLMLogModel.user_id == user_id)
            .order_by(LLMLogModel.created_at.desc())
            .limit(limit)
        )
        return [LLMLogMapper.model_to_domain(model) for model in result.scalars().all()]

    async def get_failed_logs(self, limit: int = 100) -> list[LLMLogEntry]:
        result = await self.session.execute(
            select(LLMLogModel)
            .where(LLMLogModel.error.is_not(None))
            .order_by(LLMLogModel.created_at.desc())
            .limit(limit)
        )
        return [LLMLogMapper.model_to_domain(model) for model in result.scalars().all()]

    async def get_slow_logs(self, limit: int = 100) -> list[LLMLogEntry]:
        result = await self.session.execute(
            select(LLMLogModel)
            .where(LLMLogModel.latency_ms.is_not(None), LLMLogModel.latency_ms > 3000)
            .order_by(LLMLogModel.created_at.desc())
            .limit(limit)
        )
        return [LLMLogMapper.model_to_domain(model) for model in result.scalars().all()]

    async def get_logs_by_request_type(
        self,
        request_type: LLMRequestType,
        limit: int = 100,
    ) -> list[LLMLogEntry]:
        result = await self.session.execute(
            select(LLMLogModel)
            .where(LLMLogModel.request_type == request_type.value)
            .order_by(LLMLogModel.created_at.desc())
            .limit(limit)
        )
        return [LLMLogMapper.model_to_domain(model) for model in result.scalars().all()]

    async def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[LLMLogEntry]:
        result = await self.session.execute(
            select(LLMLogModel)
            .where(
                LLMLogModel.created_at >= start_date, LLMLogModel.created_at <= end_date
            )
            .order_by(LLMLogModel.created_at.desc())
        )
        return [LLMLogMapper.model_to_domain(model) for model in result.scalars().all()]

    async def list_logs(
        self,
        offset: int = 0,
        limit: int = 100,
        request_type: LLMRequestType | None = None,
        fallback_only: bool = False,
    ) -> list[LLMLogEntry]:
        query = select(LLMLogModel).order_by(LLMLogModel.created_at.desc())
        if request_type is not None:
            query = query.where(LLMLogModel.request_type == request_type.value)
        if fallback_only:
            query = query.where(LLMLogModel.is_fallback.is_(True))

        result = await self.session.execute(query.offset(offset).limit(limit))
        return [LLMLogMapper.model_to_domain(model) for model in result.scalars().all()]

    async def count_logs(
        self,
        request_type: LLMRequestType | None = None,
        fallback_only: bool = False,
    ) -> int:
        query = select(func.count(LLMLogModel.id))
        if request_type is not None:
            query = query.where(LLMLogModel.request_type == request_type.value)
        if fallback_only:
            query = query.where(LLMLogModel.is_fallback.is_(True))

        return int(await self.session.scalar(query) or 0)

    async def get_average_latency(self) -> float | None:
        value = await self.session.scalar(
            select(func.avg(LLMLogModel.latency_ms)).where(
                LLMLogModel.latency_ms.is_not(None)
            )
        )
        return float(value) if value is not None else None

    async def get_request_counts_by_type(self) -> dict[LLMRequestType, int]:
        result = await self.session.execute(
            select(LLMLogModel.request_type, func.count(LLMLogModel.id)).group_by(
                LLMLogModel.request_type
            )
        )
        return {
            LLMRequestType(request_type): count for request_type, count in result.all()
        }
