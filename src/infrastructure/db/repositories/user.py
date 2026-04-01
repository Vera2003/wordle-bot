"""User repository implementation."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.user import TelegramId, User, UserRepository
from src.infrastructure.db.mappers.user import UserMapper
from src.infrastructure.db.models.user import UserModel


class UserRepositoryImpl(UserRepository):
    """SQLAlchemy implementation of UserRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user: User) -> None:
        """Save a user (create or update)."""
        # Check if user exists
        existing = await self.session.get(UserModel, user.id)

        if existing:
            # Update existing model from domain entity
            model_data = UserMapper.domain_to_model(user)
            existing.username = model_data.username
            existing.full_name = model_data.full_name
            existing.energy = model_data.energy
            existing.total_points = model_data.total_points
            existing.last_energy_reset = model_data.last_energy_reset
            existing.updated_at = model_data.updated_at
        else:
            # Create new model from domain entity
            model = UserMapper.domain_to_model(user)
            self.session.add(model)

        await self.session.flush()

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        model = await self.session.get(UserModel, user_id)

        if not model:
            return None

        return UserMapper.model_to_domain(model)

    async def get_by_telegram_id(self, telegram_id: TelegramId) -> Optional[User]:
        """Get user by Telegram ID."""
        query = select(UserModel).where(UserModel.telegram_id == telegram_id.value)
        result = await self.session.execute(query)
        model = result.scalars().first()

        if not model:
            return None

        return UserMapper.model_to_domain(model)

    async def delete(self, user_id: UUID) -> None:
        """Delete a user."""
        model = await self.session.get(UserModel, user_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()
