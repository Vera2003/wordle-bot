"""Achievement application layer module."""

from .commands import (
    CreateAchievementTypeCommand,
    CreateAchievementTypeHandler,
    UnlockAchievementCommand,
    UnlockAchievementHandler,
)
from .dto import AchievementProgressOutput, AchievementTypeOutput, UserAchievementOutput
from .queries import (
    GetAchievementProgressHandler,
    GetAchievementProgressQuery,
    GetAchievementTypeByIdHandler,
    GetAchievementTypeByIdQuery,
    GetAllAchievementTypesHandler,
    GetAllAchievementTypesQuery,
    GetUserAchievementsHandler,
    GetUserAchievementsQuery,
)

__all__ = [
    "AchievementTypeOutput",
    "UserAchievementOutput",
    "AchievementProgressOutput",
    "CreateAchievementTypeCommand",
    "CreateAchievementTypeHandler",
    "UnlockAchievementCommand",
    "UnlockAchievementHandler",
    "GetAchievementTypeByIdHandler",
    "GetAchievementTypeByIdQuery",
    "GetAllAchievementTypesHandler",
    "GetAllAchievementTypesQuery",
    "GetUserAchievementsHandler",
    "GetUserAchievementsQuery",
    "GetAchievementProgressHandler",
    "GetAchievementProgressQuery",
]
