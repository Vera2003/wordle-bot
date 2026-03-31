"""Mapper for Gene ORM model and domain entity."""

from src.domain.gene import Gene, GeneDifficulty, GeneName
from src.infrastructure.db.models.gene import GeneModel


class GeneMapper:
    """Mapper for Gene domain entities."""

    @staticmethod
    def model_to_domain(model: GeneModel) -> Gene:
        return Gene(
            id=model.id,
            name=GeneName(model.name),
            description=model.description,
            hint=model.hint,
            difficulty=GeneDifficulty(model.difficulty),
            is_active=model.is_active,
            created_at=model.created_at,
        )

    @staticmethod
    def domain_to_model(gene: Gene) -> GeneModel:
        return GeneModel(
            id=gene.id,
            name=gene.name.value,
            description=gene.description,
            hint=gene.hint,
            difficulty=gene.difficulty.level,
            is_active=gene.is_active,
            created_at=gene.created_at,
        )
