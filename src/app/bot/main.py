import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import redis.asyncio as aioredis

from ..core.config import settings
from .handlers import start, game, achievements, admin
from .middleware.db import DbSessionMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    
    logger.info(f"🤖 Запуск бота в режиме: {'WEBHOOK' if settings.use_webhook else 'POLLING'}")
    
    # Инициализация бота
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Redis для FSM storage
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    storage = RedisStorage(redis_client)
    
    # Диспетчер
    dp = Dispatcher(storage=storage)
    
    # Подключение к БД
    engine = create_async_engine(settings.database_url, echo=False)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    
    # Middleware
    dp.update.middleware(DbSessionMiddleware(sessionmaker, redis_client))
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(achievements.router)
    dp.include_router(admin.router)
    
    try:
        if settings.use_webhook:
            # Webhook режим - НЕ запускаем здесь, он запускается через FastAPI
            logger.warning("⚠️ Webhook режим включен, но bot/main.py запущен напрямую!")
            logger.warning("⚠️ Для webhook используйте: uvicorn src.app.main:app")
            logger.info("💡 Переключаюсь на polling для тестирования...")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        else:
            # Polling режим
            logger.info("📡 Polling режим активирован")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()
        await redis_client.close()


if __name__ == '__main__':
    asyncio.run(main())
