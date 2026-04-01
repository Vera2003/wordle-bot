"""Gene command handlers."""

from typing import Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.application.gene.dto import GeneOutput
from src.domain.gene import (
    Gene,
    GeneDifficulty,
    GeneName,
    GeneNotFoundError,
    GeneRepository,
)

DifficultyLevel = Literal["easy", "medium", "hard"]


def _to_gene_output(gene: Gene) -> GeneOutput:
    return GeneOutput(
        id=gene.id,
        name=gene.name.value,
        description=gene.description,
        hint=gene.hint,
        difficulty=cast(DifficultyLevel, gene.difficulty.level),
        is_active=gene.is_active,
        created_at=gene.created_at,
    )


class CreateGeneCommand(BaseModel):
    """Command to create a gene."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=10)
    description: str = Field(..., min_length=1)
    hint: str = Field(..., min_length=1)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    is_active: bool = Field(default=True)


class CreateGeneHandler:
    """Handler for CreateGene command."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, command: CreateGeneCommand) -> GeneOutput:
        gene = Gene(
            id=uuid4(),
            name=GeneName(command.name),
            description=command.description,
            hint=command.hint,
            difficulty=GeneDifficulty(command.difficulty),
            is_active=command.is_active,
        )
        await self.gene_repository.save(gene)
        return _to_gene_output(gene)


class ActivateGeneCommand(BaseModel):
    """Command to activate an existing gene."""

    model_config = ConfigDict(extra="forbid")

    gene_id: UUID


class ActivateGeneHandler:
    """Handler for ActivateGene command."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, command: ActivateGeneCommand) -> GeneOutput:
        gene = await self.gene_repository.get_by_id(command.gene_id)
        if not gene:
            raise GeneNotFoundError(f"Gene {command.gene_id} not found")

        gene.activate()
        await self.gene_repository.save(gene)
        return _to_gene_output(gene)


class DeactivateGeneCommand(BaseModel):
    """Command to deactivate an existing gene."""

    model_config = ConfigDict(extra="forbid")

    gene_id: UUID


class DeactivateGeneHandler:
    """Handler for DeactivateGene command."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, command: DeactivateGeneCommand) -> GeneOutput:
        gene = await self.gene_repository.get_by_id(command.gene_id)
        if not gene:
            raise GeneNotFoundError(f"Gene {command.gene_id} not found")

        gene.deactivate()
        await self.gene_repository.save(gene)
        return _to_gene_output(gene)


class UpdateGeneCommand(BaseModel):
    """Command to update editable gene fields."""

    model_config = ConfigDict(extra="forbid")

    gene_id: UUID
    description: str | None = None
    hint: str | None = None
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")


class UpdateGeneHandler:
    """Handler for updating an existing gene."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, command: UpdateGeneCommand) -> GeneOutput:
        gene = await self.gene_repository.get_by_id(command.gene_id)
        if not gene:
            raise GeneNotFoundError(f"Gene {command.gene_id} not found")

        if (
            command.description is None
            and command.hint is None
            and command.difficulty is None
        ):
            raise ValueError("At least one field must be provided for update")

        gene.update_details(
            description=command.description,
            hint=command.hint,
            difficulty=(
                GeneDifficulty(command.difficulty)
                if command.difficulty is not None
                else None
            ),
        )
        await self.gene_repository.save(gene)
        return _to_gene_output(gene)
