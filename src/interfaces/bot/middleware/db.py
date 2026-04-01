from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker
import redis.asyncio as aioredis


class DbSessionMiddleware(BaseMiddleware):
    """Middleware для передачи сессии БД и Redis в хендлеры"""
    
    def __init__(self, sessionmaker: async_sessionmaker, redis: aioredis.Redis):
        super().__init__()
        self.sessionmaker = sessionmaker
        self.redis = redis
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.sessionmaker() as session:
            data['db'] = session
            data['redis'] = self.redis
            return await handler(event, data)
