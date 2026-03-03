from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..core.config import Settings


def create_db_engine(settings: Settings) -> AsyncEngine:
    """
    Создать AsyncEngine с единообразными параметрами пула.
    Вызывается один раз — в lifespan (webhook) или в main() (polling).
    """
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


def create_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Создать фабрику сессий под переданный движок."""
    return async_sessionmaker(engine, expire_on_commit=False)