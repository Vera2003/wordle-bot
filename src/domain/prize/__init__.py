"""Prize domain context - bounded context for prize rewards."""

from .entities import Prize, UserPrize
from .repositories import PrizeRepository, UserPrizeRepository
from .value_objects import PrizeValue, EarnedPrizeRecord
from .errors import (
    PrizeError,
    PrizeNotFoundError,
    PrizeNotAvailableError,
    InsufficientPointsError,
)
from .services import PrizeService

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
