"""Shared pytest fixtures for the refactored test suite."""
from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

setattr(SQLiteTypeCompiler, "visit_big_integer", lambda self, type_, **kw: "INTEGER")

from src.infrastructure.db.base import Base
from src.infrastructure.db.models.achievement import AchievementTypeModel, UserAchievementModel  # noqa: F401
from src.infrastructure.db.models.game import GameAttemptModel, GameSessionModel  # noqa: F401
from src.infrastructure.db.models.gene import GeneModel  # noqa: F401
from src.infrastructure.db.models.llm import LLMLogModel  # noqa: F401
from src.infrastructure.db.models.prize import PrizeModel, UserPrizeModel  # noqa: F401
from src.infrastructure.db.models.user import UserModel  # noqa: F401

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Create an isolated in-memory SQLite session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
def redis() -> AsyncMock:
    """Provide an in-memory async Redis mock."""
    store: dict = {}
    mock = AsyncMock()

    async def _get(key):
        return store.get(key)

    async def _set(key, value, ex=None):
        store[key] = str(value)

    async def _delete(*keys):
        for k in keys:
            store.pop(k, None)

    async def _exists(key):
        return key in store

    mock.get = AsyncMock(side_effect=_get)
    mock.set = AsyncMock(side_effect=_set)
    mock.delete = AsyncMock(side_effect=_delete)
    mock.exists = AsyncMock(side_effect=_exists)
    mock._store = store  # доступ из тестов

    return mock