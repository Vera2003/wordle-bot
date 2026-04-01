"""Integration tests for Gene repository."""

from uuid import uuid4

import pytest

from src.domain.gene import Gene, GeneDifficulty, GeneName
from src.infrastructure.db.repositories.gene import GeneRepositoryImpl


@pytest.mark.asyncio
async def test_gene_repository_save_and_get_by_id(db):
    repo = GeneRepositoryImpl(db)

    gene = Gene(
        id=uuid4(),
        name=GeneName("MTHFR"),
        description="Supports folate metabolism.",
        hint="Connected with folate.",
        difficulty=GeneDifficulty("medium"),
    )

    await repo.save(gene)
    loaded = await repo.get_by_id(gene.id)

    assert loaded is not None
    assert loaded.id == gene.id
    assert loaded.name.value == "MTHFR"
    assert loaded.difficulty.level == "medium"
    assert loaded.is_active is True


@pytest.mark.asyncio
async def test_gene_repository_get_by_name_normalizes_case(db):
    repo = GeneRepositoryImpl(db)

    gene = Gene(
        id=uuid4(),
        name=GeneName("APOE"),
        description="Important for lipid transport.",
        hint="Lipid transport.",
        difficulty=GeneDifficulty("easy"),
    )
    await repo.save(gene)

    loaded = await repo.get_by_name("apoe")

    assert loaded is not None
    assert loaded.id == gene.id


@pytest.mark.asyncio
async def test_gene_repository_returns_only_active_genes(db):
    repo = GeneRepositoryImpl(db)

    active_gene = Gene(
        id=uuid4(),
        name=GeneName("BRCA"),
        description="DNA repair gene.",
        hint="DNA repair.",
        difficulty=GeneDifficulty("hard"),
        is_active=True,
    )
    inactive_gene = Gene(
        id=uuid4(),
        name=GeneName("TPMT"),
        description="Drug metabolism gene.",
        hint="Drug metabolism.",
        difficulty=GeneDifficulty("easy"),
        is_active=False,
    )

    await repo.save(active_gene)
    await repo.save(inactive_gene)

    active_genes = await repo.get_active_genes()
    random_gene = await repo.get_random_active()

    assert [gene.id for gene in active_genes] == [active_gene.id]
    assert random_gene is not None
    assert random_gene.id == active_gene.id
