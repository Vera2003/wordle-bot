"""
Сервис управления энергией пользователя.

Рефакторинг:
- Добавлен _get_user() helper — нет дублирования select(User) в каждом методе
- Добавлен _cache_key() метод — ключ Redis в одном месте
- add_energy больше не вложен внутрь spend_energy (исходный критический баг)
"""
from datetime import datetime, time

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models.user import User
from ..utils.time_helpers import get_seconds_until_midnight

_ENERGY_CACHE_TTL = 3600  # 1 час


class EnergyService:
    """Управление энергией: чтение, трата, пополнение, авто-восстановление."""

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    def _cache_key(self, user_id: int) -> str:
        return f"user:{user_id}:energy"

    async def _get_user(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_energy(self, user_id: int) -> int:
        """Получить текущую энергию (с кэшем в Redis)."""
        cached = await self.redis.get(self._cache_key(user_id))
        if cached is not None:
            return int(cached)

        user = await self._get_user(user_id)
        if not user:
            return 0

        await self._check_and_restore_energy(user)
        await self.redis.set(self._cache_key(user_id), user.energy, ex=_ENERGY_CACHE_TTL)
        return user.energy

    async def spend_energy(self, user_id: int, amount: int) -> bool:
        """Потратить энергию. Возвращает False если не хватает."""
        user = await self._get_user(user_id)
        if not user or user.energy < amount:
            return False

        user.energy -= amount
        await self.db.commit()
        await self.redis.set(self._cache_key(user_id), user.energy, ex=_ENERGY_CACHE_TTL)
        return True

    async def add_energy(self, user_id: int, amount: int) -> None:
        """Добавить энергию пользователю (бонус, награда)."""
        user = await self._get_user(user_id)
        if not user:
            return

        user.energy += amount
        await self.db.commit()
        await self.redis.set(self._cache_key(user_id), user.energy, ex=_ENERGY_CACHE_TTL)

    async def restore_daily_energy(self, user_id: int) -> None:
        """Восстановить дневную энергию (вызывается по расписанию или в /resetday)."""
        user = await self._get_user(user_id)
        if not user:
            return

        user.energy = settings.daily_energy
        user.last_energy_reset = datetime.utcnow()
        await self.db.commit()
        await self.redis.set(self._cache_key(user_id), user.energy, ex=_ENERGY_CACHE_TTL)

    async def _check_and_restore_energy(self, user: User) -> None:
        """Авто-восстановление если прошли сутки (UTC)."""
        now = datetime.utcnow()
        midnight_today = datetime.combine(now.date(), time(0, 0))
        if user.last_energy_reset < midnight_today:
            user.energy = settings.daily_energy
            user.last_energy_reset = now
            await self.db.commit()