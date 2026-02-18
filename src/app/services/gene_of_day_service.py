"""
Сервис управления геном дня.

Единственное место, где хранится логика выбора и кэширования гена дня.
До этого логика дублировалась в game.py хендлере и HintService.
"""
import random

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.gene import Gene
from ..utils.time_helpers import get_seconds_until_midnight, get_today_str


class GeneOfDayService:
    """Сервис гена дня: выбор, кэширование в Redis, инвалидация."""

    REDIS_KEY_PREFIX = "gene_of_day"

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    def _cache_key(self) -> str:
        return f"{self.REDIS_KEY_PREFIX}:{get_today_str()}"

    async def get(self) -> Gene:
        """
        Вернуть ген дня.
        Берётся из Redis-кэша, если там есть и ген активен.
        Иначе — выбирается случайный активный ген и кэшируется до полуночи.
        """
        key = self._cache_key()
        cached_id = await self.redis.get(key)

        if cached_id:
            gene = await self.db.get(Gene, int(cached_id))
            if gene and gene.is_active:
                return gene
            # Ген деактивирован — инвалидируем кэш и выбираем новый
            await self.redis.delete(key)

        return await self._pick_and_cache()

    async def invalidate(self) -> None:
        """Сбросить кэш гена дня (используется в /resetday)."""
        await self.redis.delete(self._cache_key())

    async def _pick_and_cache(self) -> Gene:
        result = await self.db.execute(select(Gene).where(Gene.is_active == True))
        genes = result.scalars().all()

        if not genes:
            raise ValueError("В базе нет активных генов")

        gene = random.choice(genes)
        ttl = get_seconds_until_midnight()
        await self.redis.set(self._cache_key(), gene.id, ex=ttl)
        return gene