"""Main FastAPI application."""

from contextlib import asynccontextmanager
from dataclasses import dataclass

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.engine import create_db_engine, create_session_maker
from src.infrastructure.telemetry.logging import setup_logging
from src.interfaces.api.v1 import (
    gene_router,
    llm_router,
    prize_router,
    stats_router,
    user_router,
)
from src.interfaces.bot.main import create_bot, create_dispatcher
from src.interfaces.bot.webhook import WebhookHandler, remove_webhook, setup_webhook

setup_logging()


@dataclass
class BotRuntime:
    """Runtime objects used when FastAPI hosts the Telegram webhook."""

    bot: Bot | None = None
    dispatcher: Dispatcher | None = None
    webhook_handler: WebhookHandler | None = None
    redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    settings = get_settings()
    engine = create_db_engine(settings)
    session_maker = create_session_maker(engine)
    app.state.db_session_maker = session_maker
    app.state.bot_runtime = BotRuntime()

    if settings.use_webhook:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        bot = create_bot(settings)
        dispatcher = create_dispatcher(session_maker, redis_client)
        webhook_handler = WebhookHandler(
            bot=bot,
            dp=dispatcher,
            secret_token=settings.webhook_secret,
        )
        app.state.bot_runtime = BotRuntime(
            bot=bot,
            dispatcher=dispatcher,
            webhook_handler=webhook_handler,
            redis_client=redis_client,
        )
        await setup_webhook(
            bot=bot,
            webhook_url=settings.webhook_url,
            secret_token=settings.webhook_secret,
        )

    yield

    bot_runtime: BotRuntime = app.state.bot_runtime
    if bot_runtime.bot is not None:
        await remove_webhook(bot_runtime.bot)
        await bot_runtime.bot.session.close()
    if bot_runtime.redis_client is not None:
        await bot_runtime.redis_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Wordle Bot API",
        description="Async API for Telegram Wordle bot",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(user_router, prefix="/api/v1")
    app.include_router(stats_router, prefix="/api/v1")
    app.include_router(gene_router, prefix="/api/v1")
    app.include_router(prize_router, prefix="/api/v1")
    app.include_router(llm_router, prefix="/api/v1")

    if settings.use_webhook:

        @app.post(settings.webhook_path)
        async def telegram_webhook(request: Request):
            """Receive Telegram webhook updates through the refactored bot interface layer."""
            bot_runtime: BotRuntime = request.app.state.bot_runtime
            if bot_runtime.webhook_handler is None:
                return {"status": "webhook not initialized"}
            return await bot_runtime.webhook_handler.handle(request)

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
