"""Prize repository implementations."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.prize import Prize, PrizeRepository, UserPrize, UserPrizeRepository
from src.infrastructure.db.mappers.prize import PrizeMapper, UserPrizeMapper
from src.infrastructure.db.models.prize import PrizeModel, UserPrizeModel


class PrizeRepositoryImpl(PrizeRepository):
    """SQLAlchemy implementation of PrizeRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, prize: Prize) -> None:
        existing = await self.session.get(PrizeModel, prize.id)
        if existing:
            existing.name = prize.name
            existing.title = prize.title
            existing.description = prize.description
            existing.prize_value = prize.value.value
            existing.is_active = prize.is_active
        else:
            self.session.add(PrizeMapper.domain_to_model(prize))
        await self.session.flush()

    async def get_by_id(self, prize_id: UUID) -> Optional[Prize]:
        model = await self.session.get(PrizeModel, prize_id)
        return PrizeMapper.model_to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Optional[Prize]:
        result = await self.session.execute(select(PrizeModel).where(PrizeModel.name == name.lower().strip()))
        model = result.scalars().first()
        return PrizeMapper.model_to_domain(model) if model else None

    async def get_active_prizes(self) -> list[Prize]:
        result = await self.session.execute(
            select(PrizeModel)
            .where(PrizeModel.is_active == True)
            .order_by(PrizeModel.created_at.desc())
        )
        return [PrizeMapper.model_to_domain(model) for model in result.scalars().all()]

    async def delete(self, prize_id: UUID) -> None:
        model = await self.session.get(PrizeModel, prize_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()


class UserPrizeRepositoryImpl(UserPrizeRepository):
    """SQLAlchemy implementation of UserPrizeRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user_prize: UserPrize) -> None:
        existing = await self.session.get(UserPrizeModel, user_prize.id)
        if existing:
            existing.user_id = user_prize.user_id
            existing.prize_id = user_prize.prize_id
            existing.is_used = user_prize.is_used
            existing.awarded_at = user_prize.awarded_at
            existing.used_at = user_prize.used_at
        else:
            self.session.add(UserPrizeMapper.domain_to_model(user_prize))
        await self.session.flush()

    async def get_by_id(self, user_prize_id: UUID) -> Optional[UserPrize]:
        model = await self.session.get(UserPrizeModel, user_prize_id)
        return UserPrizeMapper.model_to_domain(model) if model else None

    async def get_user_prizes(self, user_id: UUID, used_only: bool = False) -> list[UserPrize]:
        query = select(UserPrizeModel).where(UserPrizeModel.user_id == user_id)
        if used_only:
            query = query.where(UserPrizeModel.is_used == True)
        query = query.order_by(UserPrizeModel.awarded_at.desc())
        result = await self.session.execute(query)
        return [UserPrizeMapper.model_to_domain(model) for model in result.scalars().all()]

    async def get_unused_prizes(self, user_id: UUID) -> list[UserPrize]:
        result = await self.session.execute(
            select(UserPrizeModel)
            .where(UserPrizeModel.user_id == user_id, UserPrizeModel.is_used == False)
            .order_by(UserPrizeModel.awarded_at.desc())
        )
        return [UserPrizeMapper.model_to_domain(model) for model in result.scalars().all()]

    async def delete(self, user_prize_id: UUID) -> None:
        model = await self.session.get(UserPrizeModel, user_prize_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()
