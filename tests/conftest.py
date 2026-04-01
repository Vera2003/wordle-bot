"""Shared pytest fixtures for the refactored test suite."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.infrastructure.db.base import Base
from src.infrastructure.db.models.achievement import (  # noqa: F401
    AchievementTypeModel,
    UserAchievementModel,
)
from src.infrastructure.db.models.game import GameAttemptModel  # noqa: F401
from src.infrastructure.db.models.game import GameSessionModel  # noqa: F401
from src.infrastructure.db.models.gene import GeneModel  # noqa: F401
from src.infrastructure.db.models.llm import LLMLogModel  # noqa: F401
from src.infrastructure.db.models.prize import PrizeModel, UserPrizeModel  # noqa: F401
from src.infrastructure.db.models.user import UserModel  # noqa: F401

setattr(SQLiteTypeCompiler, "visit_big_integer", lambda self, type_, **kw: "INTEGER")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Assign default markers based on the test directory."""
    for item in items:
        path = Path(str(item.fspath))
        parts = path.parts
        if "unit" in parts:
            item.add_marker(pytest.mark.unit)
        if "integration" in parts:
            item.add_marker(pytest.mark.integration)
        if "e2e" in parts:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.smoke)


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
