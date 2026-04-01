"""Bot entrypoints and dispatcher wiring."""

from __future__ import annotations

import asyncio

import redis.asyncio as aioredis
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.engine import create_db_engine, create_session_maker
from src.infrastructure.telemetry.logging import setup_logging
from src.interfaces.bot.handlers import achievements, admin, chat, game, start
from src.interfaces.bot.middleware.db import DbSessionMiddleware
from src.interfaces.bot.middleware.logging import LoggingMiddleware
from src.interfaces.bot.middleware.user import UserMiddleware

setup_logging()
logger = structlog.get_logger(__name__)


def create_bot(settings: Settings) -> Bot:
    """Create the Telegram bot client."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    session_maker: async_sessionmaker[AsyncSession],
    redis_client: aioredis.Redis,
) -> Dispatcher:
    """Create and wire the dispatcher, middleware, and routers."""
    storage = RedisStorage(redis_client)
    dp = Dispatcher(storage=storage)

    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(DbSessionMiddleware(session_maker, redis_client))
    dp.update.middleware(UserMiddleware())

    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(achievements.router)
    dp.include_router(admin.router)
    dp.include_router(chat.router)

    return dp


async def main() -> None:
    """Run the bot in polling mode."""
    settings = get_settings()
    bot = create_bot(settings)

    redis_client = aioredis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )

    engine = create_db_engine(settings)
    session_maker = create_session_maker(engine)
    dp = create_dispatcher(session_maker, redis_client)

    logger.info("🤖 Starting bot in polling mode...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await redis_client.aclose()
        await engine.dispose()
        await bot.session.close()
        logger.info("👋 Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
