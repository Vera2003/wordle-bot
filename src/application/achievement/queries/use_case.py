"""Achievement query handlers."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.achievement.dto import (
    AchievementProgressOutput,
    AchievementTypeOutput,
    UserAchievementOutput,
)
from src.domain.achievement import (
    AchievementService,
    AchievementType,
    AchievementTypeNotFoundError,
    AchievementTypeRepository,
    UserAchievement,
    UserAchievementRepository,
)


def _to_achievement_type_output(achievement_type: AchievementType) -> AchievementTypeOutput:
    return AchievementTypeOutput(
        id=achievement_type.id,
        name=achievement_type.name,
        title=achievement_type.title,
        description=achievement_type.description,
        requirement_value=achievement_type.requirement.value,
        reward_type=achievement_type.reward_type.value,
        reward_value=achievement_type.reward_value.value,
        created_at=achievement_type.created_at,
    )


def _to_user_achievement_output(user_achievement: UserAchievement) -> UserAchievementOutput:
    return UserAchievementOutput(
        id=user_achievement.id,
        user_id=user_achievement.user_id,
        achievement_type_id=user_achievement.achievement_type_id,
        unlocked_at=user_achievement.unlocked_at,
    )


class GetAchievementTypeByIdQuery(BaseModel):
    """Query to fetch an achievement definition by ID."""

    model_config = ConfigDict(extra="forbid")

    achievement_type_id: UUID


class GetAchievementTypeByIdHandler:
    """Handler for GetAchievementTypeById query."""

    def __init__(self, achievement_type_repository: AchievementTypeRepository):
        self.achievement_type_repository = achievement_type_repository

    async def __call__(self, query: GetAchievementTypeByIdQuery) -> AchievementTypeOutput:
        achievement_type = await self.achievement_type_repository.get_by_id(query.achievement_type_id)
        if not achievement_type:
            raise AchievementTypeNotFoundError(
                f"Achievement {query.achievement_type_id} not found"
            )
        return _to_achievement_type_output(achievement_type)


class GetAllAchievementTypesQuery(BaseModel):
    """Query to fetch all achievement definitions."""

    model_config = ConfigDict(extra="forbid")


class GetAllAchievementTypesHandler:
    """Handler for GetAllAchievementTypes query."""

    def __init__(self, achievement_type_repository: AchievementTypeRepository):
        self.achievement_type_repository = achievement_type_repository

    async def __call__(self, query: GetAllAchievementTypesQuery) -> list[AchievementTypeOutput]:
        del query
        achievement_types = await self.achievement_type_repository.get_all()
        return [_to_achievement_type_output(item) for item in achievement_types]


class GetUserAchievementsQuery(BaseModel):
    """Query to fetch achievements unlocked by a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class GetUserAchievementsHandler:
    """Handler for GetUserAchievements query."""

    def __init__(self, user_achievement_repository: UserAchievementRepository):
        self.user_achievement_repository = user_achievement_repository

    async def __call__(self, query: GetUserAchievementsQuery) -> list[UserAchievementOutput]:
        achievements = await self.user_achievement_repository.get_user_achievements(query.user_id)
        return [_to_user_achievement_output(item) for item in achievements]


class GetAchievementProgressQuery(BaseModel):
    """Query to calculate progress for a user toward an achievement."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    achievement_type_id: UUID
    current_progress: int = Field(..., ge=0)


class GetAchievementProgressHandler:
    """Handler for GetAchievementProgress query."""

    def __init__(
        self,
        achievement_type_repository: AchievementTypeRepository,
        user_achievement_repository: UserAchievementRepository,
    ):
        self.achievement_type_repository = achievement_type_repository
        self.user_achievement_repository = user_achievement_repository

    async def __call__(self, query: GetAchievementProgressQuery) -> AchievementProgressOutput:
        achievement_type = await self.achievement_type_repository.get_by_id(query.achievement_type_id)
        if not achievement_type:
            raise AchievementTypeNotFoundError(
                f"Achievement {query.achievement_type_id} not found"
            )

        existing = await self.user_achievement_repository.get_by_user_and_achievement(
            user_id=query.user_id,
            achievement_type_id=query.achievement_type_id,
        )
        progress_percent = AchievementService.calculate_progress(
            achievement_type=achievement_type,
            current_value=query.current_progress,
        )
        return AchievementProgressOutput(
            achievement=_to_achievement_type_output(achievement_type),
            current_progress=query.current_progress,
            progress_percent=progress_percent,
            is_unlocked=existing is not None,
        )
