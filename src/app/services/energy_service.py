from datetime import datetime, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from ..db.models.user import User
from ..core.config import settings

from ..utils.time_helpers import get_seconds_until_midnight

class EnergyService:
    """Сервис управления энергией"""
    
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis
    
    async def get_user_energy(self, user_id: int) -> int:  # ← убрали один уровень отступа
        """Получает текущую энергию пользователя"""
        cache_key = f"user:{user_id}:energy"
        cached_energy = await self.redis.get(cache_key)
        
        if cached_energy:
            return int(cached_energy)
        
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return 0
        
        await self._check_and_restore_energy(user)
        
        # Кешируем на 1 час
        await self.redis.set(cache_key, user.energy, ex=3600)
        
        return user.energy
    

    async def spend_energy(self, user_id: int, amount: int) -> bool:
        """Тратит энергию"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or user.energy < amount:
            return False
        
        user.energy -= amount
        await self.db.commit()
        
        cache_key = f"user:{user_id}:energy"
        await self.redis.set(cache_key, user.energy, ex=3600)
        
        return True
    

        async def add_energy(self, user_id: int, amount: int):
            """Добавляет энергию"""
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                user.energy += amount
                await self.db.commit()
                
                cache_key = f"user:{user_id}:energy"
                await self.redis.set(cache_key, user.energy, ex=3600)
            
    
    async def _check_and_restore_energy(self, user: User):
        """Проверяет и восстанавливает энергию, если прошли сутки"""
        now = datetime.utcnow()
        midnight_today = datetime.combine(now.date(), time(0, 0))
        
        # Если последний сброс был до сегодняшней полуночи
        if user.last_energy_reset < midnight_today:
            user.energy = settings.daily_energy
            user.last_energy_reset = now
            await self.db.commit()
    
    async def restore_daily_energy(self, user_id: int):
        """Восстанавливает дневную энергию (вызывается по расписанию)"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.energy = settings.daily_energy
            user.last_energy_reset = datetime.utcnow()
            await self.db.commit()
            
            # Обновляем кеш
            cache_key = f"user:{user_id}:energy"
            await self.redis.set(cache_key, user.energy, ex=3600)
