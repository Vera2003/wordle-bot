from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import redis.asyncio as aioredis
import structlog

from .core.config import settings
from .api.v1 import genes, stats, prizes
from .db.session import engine
from .bot.webhook import WebhookHandler, setup_webhook, remove_webhook
from .bot.handlers import start, game, achievements, admin
from .bot.middleware.db import DbSessionMiddleware
from .bot.middleware.logging import LoggingMiddleware  # ← ДОБАВИЛИ

# ⚡ ВАЖНО: Импортируем все модели до использования
from .db.models.user import User
from .db.models.gene import Gene
from .db.models.game import GameSession, GameAttempt
from .db.models.achievements import AchievementType, UserAchievement
from .db.models.prize import PrizeType, UserPrize

logger = structlog.getLogger(__name__)

# Глобальные объекты для бота (только если webhook)
bot: Bot | None = None
dp: Dispatcher | None = None
webhook_handler: WebhookHandler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    global bot, dp, webhook_handler
    
    # === STARTUP ===
    logger.info("🚀 FastAPI запускается...")
    
    # Если включен webhook режим, инициализируем бота
    if settings.use_webhook:
        logger.info("🔗 Webhook режим активирован")
        
        if not settings.webhook_domain:
            raise ValueError("❌ WEBHOOK_DOMAIN не установлен в .env!")
        
        # Инициализация бота
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Redis для FSM
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        storage = RedisStorage(redis_client)
        
        # Диспетчер
        dp = Dispatcher(storage=storage)
        
        # Подключение к БД
        engine_bot = create_async_engine(settings.database_url, echo=False)
        sessionmaker = async_sessionmaker(engine_bot, expire_on_commit=False)
        
        # ========== MIDDLEWARE (ПОРЯДОК ВАЖЕН!) ==========
        # 1. Сначала LoggingMiddleware (чтобы логировать ВСЕ события)
        dp.update.middleware(LoggingMiddleware())
        logger.info("🔍 DEBUG: LoggingMiddleware registered")

        # 2. Затем DbSessionMiddleware (для доступа к БД и Redis)
        dp.update.middleware(DbSessionMiddleware(sessionmaker, redis_client))
        logger.info("🔍 DEBUG: DbSessionMiddleware registered")

        # ==================================================
        
        # Регистрация роутеров
        dp.include_router(start.router)
        dp.include_router(game.router)
        dp.include_router(achievements.router)
        dp.include_router(admin.router)
        logger.info("🔍 DEBUG: All routers registered")

        # Создаём webhook handler
        webhook_handler = WebhookHandler(
            bot=bot,
            dp=dp,
            secret_token=settings.webhook_secret
        )
        
        # Настраиваем webhook в Telegram
        await setup_webhook(
            bot=bot,
            webhook_url=settings.webhook_url,
            secret_token=settings.webhook_secret
        )
        
        logger.info(f"✅ Webhook настроен: {settings.webhook_url}")
        logger.info("📊 LoggingMiddleware активирован")  # ← ДОБАВИЛИ
    else:
        logger.info("📡 Webhook отключен (используйте polling)")
    
    yield
    
    # === SHUTDOWN ===
    logger.info("👋 FastAPI останавливается...")
    
    if bot:
        await remove_webhook(bot)
        await bot.session.close()
    
    await engine.dispose()


app = FastAPI(
    title="Genetic Wordle Admin API",
    description="API для администрирования игры Genetic Wordle",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus метрики
Instrumentator().instrument(app).expose(app)

# Webhook endpoint (только если webhook включен)
if settings.use_webhook:
    @app.post(settings.webhook_path)
    async def telegram_webhook(request: Request):
        """Endpoint для приёма обновлений от Telegram"""
        if webhook_handler:
            return await webhook_handler.handle(request)
        return {"status": "webhook not initialized"}

# API роуты
app.include_router(genes.router, prefix="/api/v1/genes", tags=["Genes"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
app.include_router(prizes.router, prefix="/api/v1/prizes", tags=["Prizes"])


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "genetic-wordle-api",
        "version": "0.1.0",
        "webhook_enabled": settings.use_webhook,
        "webhook_url": settings.webhook_url if settings.use_webhook else None
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}