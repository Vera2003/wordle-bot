"""Gene query handlers."""

from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.gene.dto import GeneOutput, GeneSummaryOutput
from src.domain.gene import Gene, GeneNotFoundError, GeneRepository


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


def _to_gene_summary(gene: Gene) -> GeneSummaryOutput:
    return GeneSummaryOutput(
        id=gene.id,
        name=gene.name.value,
        difficulty=cast(DifficultyLevel, gene.difficulty.level),
        is_active=gene.is_active,
    )


class GetGeneByIdQuery(BaseModel):
    """Query to fetch a gene by ID."""

    model_config = ConfigDict(extra="forbid")

    gene_id: UUID


class GetGeneByIdHandler:
    """Handler for GetGeneById query."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, query: GetGeneByIdQuery) -> GeneOutput:
        gene = await self.gene_repository.get_by_id(query.gene_id)
        if not gene:
            raise GeneNotFoundError(f"Gene {query.gene_id} not found")
        return _to_gene_output(gene)


class GetActiveGenesQuery(BaseModel):
    """Query to fetch all active genes."""

    model_config = ConfigDict(extra="forbid")


class GetActiveGenesHandler:
    """Handler for GetActiveGenes query."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, query: GetActiveGenesQuery) -> list[GeneSummaryOutput]:
        del query
        genes = await self.gene_repository.get_active_genes()
        return [_to_gene_summary(gene) for gene in genes]


class ListGenesQuery(BaseModel):
    """Query to fetch all genes for admin screens."""

    model_config = ConfigDict(extra="forbid")


class ListGenesHandler:
    """Handler for listing all genes."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, query: ListGenesQuery) -> list[GeneOutput]:
        del query
        genes = await self.gene_repository.get_all_genes()
        return [_to_gene_output(gene) for gene in genes]


class GetRandomActiveGeneQuery(BaseModel):
    """Query to fetch one random active gene."""

    model_config = ConfigDict(extra="forbid")


class GetRandomActiveGeneHandler:
    """Handler for GetRandomActiveGene query."""

    def __init__(self, gene_repository: GeneRepository):
        self.gene_repository = gene_repository

    async def __call__(self, query: GetRandomActiveGeneQuery) -> GeneOutput:
        del query
        gene = await self.gene_repository.get_random_active()
        if not gene:
            raise GeneNotFoundError("No active genes found")
        return _to_gene_output(gene)
