"""
Точка входа бота в polling-режиме (для локальной разработки).

Запуск:  poetry run python -m src.app.bot.main
         task dev

Webhook-режим (production): src/app/main.py (uvicorn)

ИСПРАВЛЕНО: импорты были 'from .bot.handlers' — неверно для файла внутри пакета bot/.
Правильно: 'from .handlers'.
"""
import asyncio

import redis.asyncio as aioredis
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .handlers import achievements, admin, game, start
from .middleware.db import DbSessionMiddleware
from .middleware.logging import LoggingMiddleware
from .middleware.user import UserMiddleware
from ..core.config import settings
from ..core.logging_config import setup_logging

# Импортируем все модели чтобы SQLAlchemy их видел
from ..db.models.achievements import AchievementType, UserAchievement  # noqa: F401
from ..db.models.game import GameAttempt, GameSession  # noqa: F401
from ..db.models.gene import Gene  # noqa: F401
from ..db.models.prize import PrizeType, UserPrize  # noqa: F401
from ..db.models.user import User  # noqa: F401

setup_logging()
logger = structlog.get_logger(__name__)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    redis_client = aioredis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )
    storage = RedisStorage(redis_client)
    dp = Dispatcher(storage=storage)

    engine = create_async_engine(settings.database_url, echo=False)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    # Порядок middleware важен: Logging → DbSession → User
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(DbSessionMiddleware(sessionmaker, redis_client))
    dp.update.middleware(UserMiddleware())

    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(achievements.router)
    dp.include_router(admin.router)

    logger.info("🤖 Starting bot in polling mode...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await engine.dispose()
        await bot.session.close()
        logger.info("👋 Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())