"""Gene domain context - bounded context for genes/words."""

from .entities import Gene
from .errors import (
    GeneError,
    GeneNotFoundError,
    InvalidGeneNameError,
    GeneDifficultyError,
    GeneNotActiveError,
)
from .repositories import GeneRepository
from .services import GeneService
from .value_objects import GeneName, GeneDifficulty

__all__ = [
    # Entities
    "Gene",
    # Errors
    "GeneError",
    "GeneNotFoundError",
    "InvalidGeneNameError",
    "GeneDifficultyError",
    "GeneNotActiveError",
    # Repositories
    "GeneRepository",
    # Services
    "GeneService",
    # Value Objects
    "GeneName",
    "GeneDifficulty",
]
