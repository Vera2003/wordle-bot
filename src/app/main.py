"""
Точка входа FastAPI приложения (webhook-режим).

Для polling-режима (разработка) используйте: python -m src.app.bot_polling
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass

import redis.asyncio as aioredis
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .api.v1 import genes, prizes, stats, users
from .bot.handlers import achievements, admin, game, start
from .bot.middleware.db import DbSessionMiddleware
from .bot.middleware.logging import LoggingMiddleware
from .bot.middleware.user import UserMiddleware
from .bot.webhook import WebhookHandler, remove_webhook, setup_webhook
from .core.config import get_settings
from .core.logging_config import setup_logging
from .db.engine import create_db_engine, create_session_maker

# Импортируем все модели, чтобы Alembic их видел
from .db.models.achievements import AchievementType, UserAchievement  # noqa: F401
from .db.models.game import GameAttempt, GameSession  # noqa: F401
from .db.models.gene import Gene  # noqa: F401
from .db.models.prize import PrizeType, UserPrize  # noqa: F401
from .db.models.user import User  # noqa: F401

setup_logging()
logger = structlog.get_logger(__name__)


@dataclass
class AppState:
    bot: Bot | None = None
    dp: Dispatcher | None = None
    webhook_handler: WebhookHandler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    state = AppState()
    app.state.app_state = state

    # Единственный движок на всё приложение — используется и API, и ботом
    engine = create_db_engine(settings)
    session_maker = create_session_maker(engine)
    app.state.db_engine = engine
    app.state.db_session_maker = session_maker

    logger.info("🚀 FastAPI starting up")

    if settings.use_webhook:
        if not settings.webhook_domain:
            raise ValueError("WEBHOOK_DOMAIN не установлен в .env!")

        redis_client = aioredis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True
        )

        state.bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        storage = RedisStorage(redis_client)
        state.dp = Dispatcher(storage=storage)

        # Бот использует тот же session_maker, что и API — один пул соединений
        state.dp.update.middleware(LoggingMiddleware())
        state.dp.update.middleware(DbSessionMiddleware(session_maker, redis_client))
        state.dp.update.middleware(UserMiddleware())

        state.dp.include_router(start.router)
        state.dp.include_router(game.router)
        state.dp.include_router(achievements.router)
        state.dp.include_router(admin.router)

        state.webhook_handler = WebhookHandler(
            bot=state.bot, dp=state.dp, secret_token=settings.webhook_secret
        )
        await setup_webhook(
            bot=state.bot,
            webhook_url=settings.webhook_url,
            secret_token=settings.webhook_secret,
        )
        logger.info("✅ Webhook configured", url=settings.webhook_url)
    else:
        logger.info("📡 Webhook disabled — use polling mode (task dev)")

    yield

    logger.info("👋 FastAPI shutting down")

    if state.bot:
        await remove_webhook(state.bot)
        await state.bot.session.close()

    # Единственное место закрытия движка
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Genetic Wordle Admin API",
        description="API для администрирования Genetic Wordle",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["X-Admin-API-Key", "Content-Type"],
    )

    Instrumentator().instrument(app).expose(app)

    app.include_router(genes.router, prefix="/api/v1/genes", tags=["Genes"])
    app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
    app.include_router(prizes.router, prefix="/api/v1/prizes", tags=["Prizes"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

    if settings.use_webhook:
        @app.post(settings.webhook_path)
        async def telegram_webhook(request: Request):
            state: AppState = request.app.state.app_state
            if state.webhook_handler:
                return await state.webhook_handler.handle(request)
            return {"status": "webhook not initialized"}

    @app.get("/")
    async def root():
        return {
            "status": "ok",
            "service": "genetic-wordle-api",
            "version": "0.1.0",
            "webhook_enabled": settings.use_webhook,
            "webhook_url": settings.webhook_url if settings.use_webhook else None,
        }

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/webhook/status")
    async def webhook_status(request: Request) -> dict:
        state: AppState = request.app.state.app_state
        if state.bot:
            info = await state.bot.get_webhook_info()
            return {
                "url": info.url,
                "pending_update_count": info.pending_update_count,
                "last_error_message": info.last_error_message,
            }
        return {"error": "Bot not initialized"}

    return app


app = create_app()