"""LLM command handlers."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.llm.dto import ChatAnswerOutput, GeneFactOutput
from src.application.llm.interfaces import LLMGenerationService


class GenerateGeneFactCommand(BaseModel):
    """Command to generate one short fact about a gene."""

    model_config = ConfigDict(extra="forbid")

    gene_name: str = Field(..., min_length=3, max_length=10)
    gene_description: str = Field(..., min_length=20)
    user_id: UUID | None = None


class GenerateGeneFactHandler:
    """Handler for gene fact generation."""

    def __init__(self, llm_generation_service: LLMGenerationService):
        self.llm_generation_service = llm_generation_service

    async def __call__(self, command: GenerateGeneFactCommand) -> GeneFactOutput:
        completion = await self.llm_generation_service.generate_gene_fact(
            gene_name=command.gene_name,
            gene_description=command.gene_description,
            user_id=command.user_id,
        )
        return GeneFactOutput(
            gene_name=command.gene_name,
            fact=completion.text,
            is_fallback=completion.is_fallback,
            latency_ms=completion.latency_ms,
        )


class ChatHistoryItem(BaseModel):
    """One prior chat message."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., pattern="^(user|assistant)$")
    text: str = Field(..., min_length=1, max_length=2000)


class AskGeneticsQuestionCommand(BaseModel):
    """Command to ask the llm a genetics question."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=1000)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=10)
    user_id: UUID | None = None


class AskGeneticsQuestionHandler:
    """Handler for genetics chat."""

    def __init__(self, llm_generation_service: LLMGenerationService):
        self.llm_generation_service = llm_generation_service

    async def __call__(self, command: AskGeneticsQuestionCommand) -> ChatAnswerOutput:
        completion = await self.llm_generation_service.answer_genetics_question(
            question=command.question,
            history=[(item.role, item.text) for item in command.history],
            user_id=command.user_id,
        )
        return ChatAnswerOutput(
            question=command.question,
            answer=completion.text,
            is_fallback=completion.is_fallback,
            latency_ms=completion.latency_ms,
        )