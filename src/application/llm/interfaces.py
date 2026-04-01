"""Application-level llm ports."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .dto import LLMCompletionOutput


class LLMGenerationService(Protocol):
    """Port used by llm command handlers to generate text."""

    async def generate_gene_fact(
        self,
        gene_name: str,
        gene_description: str,
        user_id: UUID | None = None,
    ) -> LLMCompletionOutput: ...

    async def answer_genetics_question(
        self,
        question: str,
        history: list[tuple[str, str]],
        user_id: UUID | None = None,
    ) -> LLMCompletionOutput: ...
