"""Database engine creation utilities."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.config.settings import Settings


def create_db_engine(settings: Settings) -> AsyncEngine:
    """Create AsyncEngine with consistent pool configuration."""
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


def create_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session maker for the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)
