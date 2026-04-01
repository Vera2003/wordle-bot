"""Prize domain context - bounded context for prize rewards."""

from .entities import Prize, UserPrize
from .errors import (
    InsufficientPointsError,
    PrizeError,
    PrizeNotAvailableError,
    PrizeNotFoundError,
)
from .repositories import PrizeRepository, UserPrizeRepository
from .services import PrizeService
from .value_objects import EarnedPrizeRecord, PrizeValue

__all__ = [
    # Entities
    "Prize",
    "UserPrize",
    # Repositories (ports)
    "PrizeRepository",
    "UserPrizeRepository",
    # Value Objects
    "PrizeValue",
    "EarnedPrizeRecord",
    # Errors
    "PrizeError",
    "PrizeNotFoundError",
    "PrizeNotAvailableError",
    "InsufficientPointsError",
    # Services
    "PrizeService",
]
