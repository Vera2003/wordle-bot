"""Integration tests for LLM log repository."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.llm import LLMLogEntry, LLMModel, LLMLatency, LLMPrompt, LLMRequestType, LLMResponse
from src.infrastructure.db.repositories.llm import LLMLogRepositoryImpl


@pytest.mark.asyncio
async def test_llm_repository_save_and_get_by_id(db):
    repo = LLMLogRepositoryImpl(db)

    log_entry = LLMLogEntry(
        id=uuid4(),
        request_type=LLMRequestType.FACT,
        model=LLMModel.YANDEX_GPT,
        prompt=LLMPrompt("Tell me an interesting fact about APOE."),
        response=LLMResponse("APOE influences lipid transport.", is_fallback=False),
        latency=LLMLatency(850),
        error=None,
        created_at=datetime(2026, 1, 3, 10, 0, 0),
    )

    await repo.save(log_entry)
    loaded = await repo.get_by_id(log_entry.id)

    assert loaded is not None
    assert loaded.id == log_entry.id
    assert loaded.request_type == LLMRequestType.FACT
    assert loaded.response.text == "APOE influences lipid transport."


@pytest.mark.asyncio
async def test_llm_repository_filters_failed_slow_type_and_date_range(db):
    repo = LLMLogRepositoryImpl(db)
    user_id = uuid4()

    ok_entry = LLMLogEntry(
        id=uuid4(),
        request_type=LLMRequestType.FACT,
        model=LLMModel.YANDEX_GPT,
        prompt=LLMPrompt("Fact prompt"),
        response=LLMResponse("Normal response", is_fallback=False),
        latency=LLMLatency(500),
        user_id=user_id,
        error=None,
        created_at=datetime(2026, 1, 3, 10, 0, 0),
    )
    failed_entry = LLMLogEntry(
        id=uuid4(),
        request_type=LLMRequestType.CHAT,
        model=LLMModel.YANDEX_GPT,
        prompt=LLMPrompt("Chat prompt"),
        response=LLMResponse(None, is_fallback=True),
        latency=LLMLatency(4500),
        user_id=user_id,
        error="timeout",
        created_at=datetime(2026, 1, 4, 10, 0, 0),
    )

    await repo.save(ok_entry)
    await repo.save(failed_entry)

    user_logs = await repo.get_user_logs(user_id)
    failed_logs = await repo.get_failed_logs()
    slow_logs = await repo.get_slow_logs()
    chat_logs = await repo.get_logs_by_request_type(LLMRequestType.CHAT)
    range_logs = await repo.get_logs_by_date_range(
        datetime(2026, 1, 4, 0, 0, 0),
        datetime(2026, 1, 4, 23, 59, 59),
    )

    assert len(user_logs) == 2
    assert [item.id for item in failed_logs] == [failed_entry.id]
    assert [item.id for item in slow_logs] == [failed_entry.id]
    assert [item.id for item in chat_logs] == [failed_entry.id]
    assert [item.id for item in range_logs] == [failed_entry.id]
