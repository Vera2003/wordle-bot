from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from .core.config import settings
from .api.v1 import genes, stats, prizes
from .db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    # Startup
    print("🚀 FastAPI запущен")
    yield
    # Shutdown
    await engine.dispose()
    print("👋 FastAPI остановлен")


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

# Подключение роутеров
app.include_router(genes.router, prefix="/api/v1/genes", tags=["Genes"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
app.include_router(prizes.router, prefix="/api/v1/prizes", tags=["Prizes"])


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "genetic-wordle-api",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
