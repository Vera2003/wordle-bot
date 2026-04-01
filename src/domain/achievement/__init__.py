"""Achievement domain context - bounded context for player achievements."""

from .entities import AchievementType, UserAchievement
from .errors import (
    AchievementAlreadyUnlockedError,
    AchievementError,
    AchievementRequirementNotMetError,
    AchievementTypeNotFoundError,
    InvalidAchievementRequirementError,
)
from .repositories import AchievementTypeRepository, UserAchievementRepository
from .services import AchievementService
from .value_objects import AchievementRequirement, RewardType, RewardValue

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
