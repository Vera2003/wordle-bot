"""Achievement command handlers."""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.application.achievement.dto import AchievementTypeOutput, UserAchievementOutput
from src.domain.achievement import (
    AchievementAlreadyUnlockedError,
    AchievementRequirement,
    AchievementService,
    AchievementType,
    AchievementTypeNotFoundError,
    AchievementTypeRepository,
    RewardType,
    RewardValue,
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


class CreateAchievementTypeCommand(BaseModel):
    """Command to create an achievement definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=255)
    requirement_value: int = Field(..., gt=0)
    reward_type: RewardType
    reward_value: str = Field(..., min_length=1, max_length=100)


class CreateAchievementTypeHandler:
    """Handler for CreateAchievementType command."""

    def __init__(self, achievement_type_repository: AchievementTypeRepository):
        self.achievement_type_repository = achievement_type_repository

    async def __call__(self, command: CreateAchievementTypeCommand) -> AchievementTypeOutput:
        achievement_type = AchievementType(
            id=uuid4(),
            name=command.name,
            title=command.title,
            description=command.description,
            requirement=AchievementRequirement(command.requirement_value),
            reward_type=command.reward_type,
            reward_value=RewardValue(command.reward_value),
        )
        await self.achievement_type_repository.save(achievement_type)
        return _to_achievement_type_output(achievement_type)


class UnlockAchievementCommand(BaseModel):
    """Command to unlock an achievement for a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    achievement_type_id: UUID
    current_progress: int = Field(..., ge=0)


class UnlockAchievementHandler:
    """Handler for UnlockAchievement command."""

    def __init__(
        self,
        achievement_type_repository: AchievementTypeRepository,
        user_achievement_repository: UserAchievementRepository,
    ):
        self.achievement_type_repository = achievement_type_repository
        self.user_achievement_repository = user_achievement_repository

    async def __call__(self, command: UnlockAchievementCommand) -> UserAchievementOutput:
        achievement_type = await self.achievement_type_repository.get_by_id(command.achievement_type_id)
        if not achievement_type:
            raise AchievementTypeNotFoundError(
                f"Achievement {command.achievement_type_id} not found"
            )

        existing = await self.user_achievement_repository.get_by_user_and_achievement(
            user_id=command.user_id,
            achievement_type_id=command.achievement_type_id,
        )
        AchievementService.can_unlock_achievement(
            achievement_type=achievement_type,
            current_progress=command.current_progress,
            already_unlocked=existing is not None,
        )

        user_achievement = AchievementService.unlock_achievement(
            achievement_type_id=command.achievement_type_id,
            user_id=command.user_id,
        )
        await self.user_achievement_repository.save(user_achievement)
        return _to_user_achievement_output(user_achievement)
