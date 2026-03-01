"""
Точка входа FastAPI приложения (webhook-режим).

Для polling-режима (разработка) используйте: python -m src.app.bot_polling
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import redis.asyncio as aioredis
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .api.v1 import genes, prizes, stats
from .bot.handlers import achievements, admin, game, start
from .bot.middleware.db import DbSessionMiddleware
from .bot.middleware.logging import LoggingMiddleware
from .bot.middleware.user import UserMiddleware
from .bot.webhook import WebhookHandler, remove_webhook, setup_webhook
from .core.config import settings
from .core.logging_config import setup_logging
from .db.session import engine

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
    state = AppState()
    app.state.app_state = state  # храним в app.state

    logger.info("🚀 FastAPI starting up")

    if settings.use_webhook:
        if not settings.webhook_domain:
            raise ValueError("WEBHOOK_DOMAIN не установлен в .env!")

        state.bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        redis_client = aioredis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True
        )
        storage = RedisStorage(redis_client)
        state.dp = Dispatcher(storage=storage)

        engine_bot = create_async_engine(settings.database_url, echo=False)
        sessionmaker = async_sessionmaker(engine_bot, expire_on_commit=False)

        # Порядок middleware важен: Logging → DbSession → User
        state.dp.update.middleware(LoggingMiddleware())
        state.dp.update.middleware(DbSessionMiddleware(sessionmaker, redis_client))
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
    await engine.dispose()


app = FastAPI(
    title="Genetic Wordle Admin API",
    description="API для администрирования Genetic Wordle",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

if settings.use_webhook:
    @app.post(settings.webhook_path)
    async def telegram_webhook(request: Request):
        state: AppState = request.app.state.app_state
        if state.webhook_handler:
            return await state.webhook_handler.handle(request)
        return {"status": "webhook not initialized"}

app.include_router(genes.router, prefix="/api/v1/genes", tags=["Genes"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
app.include_router(prizes.router, prefix="/api/v1/prizes", tags=["Prizes"])


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