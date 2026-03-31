"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.logging_config import setup_logging
from src.infrastructure.db.engine import create_db_engine, create_session_maker
from src.interfaces.api.v1 import user_router, stats_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    settings = get_settings()
    
    # Initialize database engine and session maker
    engine = create_db_engine(settings)
    app.state.db_session_maker = create_session_maker(engine)
    
    yield
    
    # Cleanup
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
        allow_origins=settings.CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(user_router, prefix="/api/v1")
    app.include_router(stats_router, prefix="/api/v1")
    
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
