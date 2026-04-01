"""Unit tests for llm application use cases."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.llm import (
    AskGeneticsQuestionCommand,
    AskGeneticsQuestionHandler,
    ChatHistoryItem,
    GenerateGeneFactCommand,
    GenerateGeneFactHandler,
    GetLLMLogsHandler,
    GetLLMLogsQuery,
    GetLLMStatsHandler,
    GetLLMStatsQuery,
    LLMCompletionOutput,
)
from src.domain.llm import LLMLogEntry, LLMLatency, LLMModel, LLMPrompt, LLMRequestType, LLMResponse


class TestGenerateGeneFactHandler:
    @pytest.mark.asyncio
    async def test_generate_gene_fact_success(self):
        service = AsyncMock()
        service.generate_gene_fact.return_value = LLMCompletionOutput(
            text="Fact about APOE",
            is_fallback=False,
            latency_ms=42,
        )

        handler = GenerateGeneFactHandler(service)
        result = await handler(
            GenerateGeneFactCommand(
                gene_name="APOE",
                gene_description="A gene involved in lipid transport and metabolism.",
            )
        )

        assert result.gene_name == "APOE"
        assert result.fact == "Fact about APOE"
        assert result.is_fallback is False
        service.generate_gene_fact.assert_called_once()


class TestAskGeneticsQuestionHandler:
    @pytest.mark.asyncio
    async def test_ask_genetics_question_success(self):
        service = AsyncMock()
        service.answer_genetics_question.return_value = LLMCompletionOutput(
            text="Genes store hereditary information.",
            is_fallback=False,
            latency_ms=55,
        )

        handler = AskGeneticsQuestionHandler(service)
        result = await handler(
            AskGeneticsQuestionCommand(
                question="What is a gene?",
                history=[ChatHistoryItem(role="user", text="Hi")],
            )
        )

        assert result.question == "What is a gene?"
        assert result.answer == "Genes store hereditary information."
        service.answer_genetics_question.assert_called_once_with(
            question="What is a gene?",
            history=[("user", "Hi")],
            user_id=None,
        )


class TestGetLLMLogsHandler:
    @pytest.mark.asyncio
    async def test_get_llm_logs_with_filters(self):
        repository = AsyncMock()
        log_entry = LLMLogEntry(
            id=uuid4(),
            request_type=LLMRequestType.CHAT,
            model=LLMModel.GPT_4O_MINI,
            prompt=LLMPrompt("Question"),
            response=LLMResponse("Answer", is_fallback=True),
            latency=LLMLatency(250),
            error=None,
            created_at=datetime(2026, 3, 31, 12, 0, 0),
        )
        repository.count_logs.return_value = 1
        repository.list_logs.return_value = [log_entry]

        handler = GetLLMLogsHandler(repository)
        result = await handler(
            GetLLMLogsQuery(request_type=LLMRequestType.CHAT, fallback_only=True)
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].request_type == "chat"
        assert result.items[0].requires_investigation is True
        repository.count_logs.assert_called_once_with(
            request_type=LLMRequestType.CHAT,
            fallback_only=True,
        )


class TestGetLLMStatsHandler:
    @pytest.mark.asyncio
    async def test_get_llm_stats_aggregates_repository_metrics(self):
        repository = AsyncMock()
        repository.count_logs.side_effect = [4, 1]
        repository.get_average_latency.return_value = 120.25
        repository.get_request_counts_by_type.return_value = {
            LLMRequestType.FACT: 3,
            LLMRequestType.CHAT: 1,
        }

        handler = GetLLMStatsHandler(repository)
        result = await handler(GetLLMStatsQuery())

        assert result.total_requests == 4
        assert result.fallback_count == 1
        assert result.fallback_rate == 25.0
        assert result.avg_latency_ms == 120.2
        assert result.requests_by_type == {"fact": 3, "chat": 1}