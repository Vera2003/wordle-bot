from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.user import User


class UserService:
    """Сервис для работы с пользователями."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID."""
        result = await self.db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ) -> User:
        """Получить или создать пользователя."""
        user = await self.get_by_telegram_id(telegram_id)

        if not user:
            from ..core.config import settings
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                energy=settings.daily_energy,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

        return user

    async def update_points(self, user_id: int, points: int) -> None:
        """Добавить очки пользователю."""
        user = await self.db.get(User, user_id)
        if user:
            user.total_points += points
            await self.db.commit()