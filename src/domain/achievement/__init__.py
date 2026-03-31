"""Achievement domain context - bounded context for player achievements."""

from .entities import AchievementType, UserAchievement
from .repositories import AchievementTypeRepository, UserAchievementRepository
from .value_objects import AchievementRequirement, RewardType, RewardValue
from .errors import (
    AchievementError,
    AchievementTypeNotFoundError,
    AchievementAlreadyUnlockedError,
    InvalidAchievementRequirementError,
    AchievementRequirementNotMetError,
)
from .services import AchievementService

__all__ = [
    # Entities
    "AchievementType",
    "UserAchievement",
    # Repositories (ports)
    "AchievementTypeRepository",
    "UserAchievementRepository",
    # Value Objects
    "AchievementRequirement",
    "RewardType",
    "RewardValue",
    # Errors
    "AchievementError",
    "AchievementTypeNotFoundError",
    "AchievementAlreadyUnlockedError",
    "InvalidAchievementRequirementError",
    "AchievementRequirementNotMetError",
    # Services
    "AchievementService",
]
