"""Mappers for achievement ORM models and domain entities."""

from src.domain.achievement import (
    AchievementRequirement,
    AchievementType,
    RewardType,
    RewardValue,
    UserAchievement,
)
from src.infrastructure.db.models.achievement import (
    AchievementTypeModel,
    UserAchievementModel,
)


class AchievementTypeMapper:
    """Mapper for AchievementType domain entity."""

    @staticmethod
    def model_to_domain(model: AchievementTypeModel) -> AchievementType:
        return AchievementType(
            id=model.id,
            name=model.name,
            title=model.title,
            description=model.description,
            requirement=AchievementRequirement(model.requirement),
            reward_type=RewardType(model.reward_type),
            reward_value=RewardValue(model.reward_value),
            created_at=model.created_at,
        )

    @staticmethod
    def domain_to_model(achievement_type: AchievementType) -> AchievementTypeModel:
        return AchievementTypeModel(
            id=achievement_type.id,
            name=achievement_type.name,
            title=achievement_type.title,
            description=achievement_type.description,
            requirement=achievement_type.requirement.value,
            reward_type=achievement_type.reward_type.value,
            reward_value=achievement_type.reward_value.value,
            created_at=achievement_type.created_at,
        )


class UserAchievementMapper:
    """Mapper for UserAchievement domain entity."""

    @staticmethod
    def model_to_domain(model: UserAchievementModel) -> UserAchievement:
        return UserAchievement(
            id=model.id,
            user_id=model.user_id,
            achievement_type_id=model.achievement_type_id,
            unlocked_at=model.unlocked_at,
        )

    @staticmethod
    def domain_to_model(user_achievement: UserAchievement) -> UserAchievementModel:
        return UserAchievementModel(
            id=user_achievement.id,
            user_id=user_achievement.user_id,
            achievement_type_id=user_achievement.achievement_type_id,
            unlocked_at=user_achievement.unlocked_at,
        )
