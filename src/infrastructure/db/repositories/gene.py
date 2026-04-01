"""Gene repository implementation."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.gene import Gene, GeneRepository
from src.infrastructure.db.mappers.gene import GeneMapper
from src.infrastructure.db.models.gene import GeneModel


class GeneRepositoryImpl(GeneRepository):
    """SQLAlchemy implementation of GeneRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, gene: Gene) -> None:
        existing = await self.session.get(GeneModel, gene.id)
        if existing:
            existing.name = gene.name.value
            existing.description = gene.description
            existing.hint = gene.hint
            existing.difficulty = gene.difficulty.level
            existing.is_active = gene.is_active
        else:
            self.session.add(GeneMapper.domain_to_model(gene))
        await self.session.flush()

    async def get_by_id(self, gene_id: UUID) -> Optional[Gene]:
        model = await self.session.get(GeneModel, gene_id)
        return GeneMapper.model_to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Optional[Gene]:
        result = await self.session.execute(
            select(GeneModel).where(GeneModel.name == name.upper().strip())
        )
        model = result.scalars().first()
        return GeneMapper.model_to_domain(model) if model else None

    async def get_active_genes(self) -> list[Gene]:
        result = await self.session.execute(
            select(GeneModel)
            .where(GeneModel.is_active.is_(True))
            .order_by(GeneModel.created_at.desc())
        )
        return [GeneMapper.model_to_domain(model) for model in result.scalars().all()]

    async def get_all_genes(self) -> list[Gene]:
        result = await self.session.execute(
            select(GeneModel).order_by(GeneModel.name.asc())
        )
        return [GeneMapper.model_to_domain(model) for model in result.scalars().all()]

    async def get_random_active(self) -> Optional[Gene]:
        result = await self.session.execute(
            select(GeneModel)
            .where(GeneModel.is_active.is_(True))
            .order_by(func.random())
            .limit(1)
        )
        model = result.scalars().first()
        return GeneMapper.model_to_domain(model) if model else None

    async def delete(self, gene_id: UUID) -> None:
        model = await self.session.get(GeneModel, gene_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()
