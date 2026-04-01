"""Unit tests for gene application use cases."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.gene import (
    ListGenesHandler,
    ListGenesQuery,
    UpdateGeneCommand,
    UpdateGeneHandler,
)
from src.domain.gene import Gene, GeneDifficulty, GeneName


class FakeGeneRepository:
    def __init__(self, genes: list[Gene]):
        self.genes = {gene.id: gene for gene in genes}

    async def save(self, gene: Gene) -> None:
        self.genes[gene.id] = gene

    async def get_by_id(self, gene_id):
        return self.genes.get(gene_id)

    async def get_by_name(self, name: str):
        normalized = name.upper().strip()
        for gene in self.genes.values():
            if gene.name.value == normalized:
                return gene
        return None

    async def get_active_genes(self):
        return [gene for gene in self.genes.values() if gene.is_active]

    async def get_all_genes(self):
        return sorted(self.genes.values(), key=lambda gene: gene.name.value)

    async def get_random_active(self):
        active = await self.get_active_genes()
        return active[0] if active else None

    async def delete(self, gene_id) -> None:
        self.genes.pop(gene_id, None)


def _make_gene(name: str, *, is_active: bool = True) -> Gene:
    return Gene(
        id=uuid4(),
        name=GeneName(name),
        description=f"Description for {name}",
        hint=f"Hint for {name}",
        difficulty=GeneDifficulty("easy"),
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_list_genes_returns_all_genes_for_admin_views():
    repository = FakeGeneRepository(
        [
            _make_gene("MTHFR", is_active=False),
            _make_gene("APOE", is_active=True),
        ]
    )

    result = await ListGenesHandler(repository)(ListGenesQuery())

    assert [item.name for item in result] == ["APOE", "MTHFR"]
    assert [item.is_active for item in result] == [True, False]


@pytest.mark.asyncio
async def test_update_gene_handler_updates_requested_field_only():
    gene = _make_gene("APOE")
    repository = FakeGeneRepository([gene])

    result = await UpdateGeneHandler(repository)(
        UpdateGeneCommand(
            gene_id=gene.id,
            description="Updated description",
            difficulty="hard",
        )
    )

    assert result.description == "Updated description"
    assert result.difficulty == "hard"
    assert result.hint == "Hint for APOE"


@pytest.mark.asyncio
async def test_update_gene_handler_requires_at_least_one_field():
    gene = _make_gene("APOE")
    repository = FakeGeneRepository([gene])

    with pytest.raises(ValueError, match="At least one field"):
        await UpdateGeneHandler(repository)(UpdateGeneCommand(gene_id=gene.id))
