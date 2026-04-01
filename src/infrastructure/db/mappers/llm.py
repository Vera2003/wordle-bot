"""Mapper for LLM log ORM model and domain entity."""

from src.domain.llm import (
    LLMLatency,
    LLMLogEntry,
    LLMModel,
    LLMPrompt,
    LLMRequestType,
    LLMResponse,
)
from src.infrastructure.db.models.llm import LLMLogModel


class LLMLogMapper:
    """Mapper for LLM log entries."""

    @staticmethod
    def model_to_domain(model: LLMLogModel) -> LLMLogEntry:
        return LLMLogEntry(
            id=model.id,
            request_type=LLMRequestType(model.request_type),
            model=LLMModel(model.model),
            prompt=LLMPrompt(model.prompt),
            response=LLMResponse(text=model.response, is_fallback=model.is_fallback),
            latency=LLMLatency(model.latency_ms),
            user_id=model.user_id,
            error=model.error,
            created_at=model.created_at,
        )

    @staticmethod
    def domain_to_model(log_entry: LLMLogEntry) -> LLMLogModel:
        return LLMLogModel(
            id=log_entry.id,
            user_id=log_entry.user_id,
            created_at=log_entry.created_at,
            request_type=log_entry.request_type.value,
            prompt=log_entry.prompt.text,
            model=log_entry.model.value,
            response=log_entry.response.text,
            is_fallback=log_entry.response.is_fallback,
            latency_ms=log_entry.latency.milliseconds,
            error=log_entry.error,
        )
