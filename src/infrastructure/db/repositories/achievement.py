"""Achievement repository implementations."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.achievement import (
    AchievementType,
    AchievementTypeRepository,
    UserAchievement,
    UserAchievementRepository,
)
from src.infrastructure.db.mappers.achievement import AchievementTypeMapper, UserAchievementMapper
from src.infrastructure.db.models.achievement import AchievementTypeModel, UserAchievementModel


class AchievementTypeRepositoryImpl(AchievementTypeRepository):
    """SQLAlchemy implementation of AchievementTypeRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, achievement_type: AchievementType) -> None:
        existing = await self.session.get(AchievementTypeModel, achievement_type.id)
        if existing:
            existing.name = achievement_type.name
            existing.title = achievement_type.title
            existing.description = achievement_type.description
            existing.requirement = achievement_type.requirement.value
            existing.reward_type = achievement_type.reward_type.value
            existing.reward_value = achievement_type.reward_value.value
        else:
            self.session.add(AchievementTypeMapper.domain_to_model(achievement_type))
        await self.session.flush()

    async def get_by_id(self, achievement_id: UUID) -> Optional[AchievementType]:
        model = await self.session.get(AchievementTypeModel, achievement_id)
        return AchievementTypeMapper.model_to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Optional[AchievementType]:
        result = await self.session.execute(
            select(AchievementTypeModel).where(AchievementTypeModel.name == name.lower().strip())
        )
        model = result.scalars().first()
        return AchievementTypeMapper.model_to_domain(model) if model else None

    async def get_all(self) -> list[AchievementType]:
        result = await self.session.execute(select(AchievementTypeModel).order_by(AchievementTypeModel.created_at.desc()))
        return [AchievementTypeMapper.model_to_domain(model) for model in result.scalars().all()]

    async def delete(self, achievement_id: UUID) -> None:
        model = await self.session.get(AchievementTypeModel, achievement_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()


class UserAchievementRepositoryImpl(UserAchievementRepository):
    """SQLAlchemy implementation of UserAchievementRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user_achievement: UserAchievement) -> None:
        existing = await self.session.get(UserAchievementModel, user_achievement.id)
        if existing:
            existing.user_id = user_achievement.user_id
            existing.achievement_type_id = user_achievement.achievement_type_id
            existing.unlocked_at = user_achievement.unlocked_at
        else:
            self.session.add(UserAchievementMapper.domain_to_model(user_achievement))
        await self.session.flush()

    async def get_by_id(self, user_achievement_id: UUID) -> Optional[UserAchievement]:
        model = await self.session.get(UserAchievementModel, user_achievement_id)
        return UserAchievementMapper.model_to_domain(model) if model else None

    async def get_by_user_and_achievement(
        self,
        user_id: UUID,
        achievement_type_id: UUID,
    ) -> Optional[UserAchievement]:
        result = await self.session.execute(
            select(UserAchievementModel).where(
                UserAchievementModel.user_id == user_id,
                UserAchievementModel.achievement_type_id == achievement_type_id,
            )
        )
        model = result.scalars().first()
        return UserAchievementMapper.model_to_domain(model) if model else None

    async def get_user_achievements(self, user_id: UUID) -> list[UserAchievement]:
        result = await self.session.execute(
            select(UserAchievementModel)
            .where(UserAchievementModel.user_id == user_id)
            .order_by(UserAchievementModel.unlocked_at.desc())
        )
        return [UserAchievementMapper.model_to_domain(model) for model in result.scalars().all()]

    async def delete(self, user_achievement_id: UUID) -> None:
        model = await self.session.get(UserAchievementModel, user_achievement_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()
