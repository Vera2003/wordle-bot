"""
Общие pytest-фикстуры.

Стратегия:
- SQLite in-memory через aiosqlite — не нужен запущенный PostgreSQL
- AsyncMock для Redis с реальным хранилищем в памяти — не нужен Redis
- Фабрики через callable-фикстуры — гибкое создание тестовых данных
- scope="function" — каждый тест получает изолированную чистую БД
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

# SQLite не поддерживает BIGINT autoincrement — только INTEGER.
# Патчим компилятор чтобы BigInteger рендерился как INTEGER в SQLite.
# Это затрагивает только тестовую среду (in-memory SQLite).
setattr(SQLiteTypeCompiler, "visit_big_integer", lambda self, type_, **kw: "INTEGER")

from src.app.db.base import Base
from src.app.db.models.achievements import AchievementType, UserAchievement  # noqa: F401
from src.app.db.models.game import GameAttempt, GameSession  # noqa: F401
from src.app.db.models.gene import Gene
from src.app.db.models.prize import PrizeType, UserPrize  # noqa: F401
from src.app.db.models.user import User


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронная сессия SQLite in-memory.

    StaticPool обязателен для in-memory SQLite — без него каждое
    соединение видит отдельную базу и таблицы "исчезают".
    """
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


# ---------------------------------------------------------------------------
# Redis mock
# ---------------------------------------------------------------------------

@pytest.fixture
def redis() -> AsyncMock:
    """
    Redis-заглушка с dict-хранилищем в памяти.

    Реализует get / set / delete / exists — достаточно для всех сервисов.
    Через mock._store можно проверять состояние кэша в тестах.
    """
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


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def make_user(db):
    async def _create(
        telegram_id=100_000,
        username="test_user",
        full_name="Test User",
        energy=6,
        total_points=0,
    ):
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            energy=energy,
            total_points=total_points,
            last_energy_reset=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    return _create


@pytest_asyncio.fixture
async def make_gene(db):
    async def _create(
        name="MTHFR",
        description="Участвует в метаболизме фолиевой кислоты и гомоцистеина.",
        hint="Важен для обмена фолиевой кислоты",
        difficulty="easy",
        is_active=True,
    ):
        gene = Gene(
            name=name,
            description=description,
            hint=hint,
            difficulty=difficulty,
            is_active=is_active,
        )
        db.add(gene)
        await db.commit()
        await db.refresh(gene)
        return gene

    return _create


@pytest_asyncio.fixture
async def make_game_session(db):
    async def _create(
        user_id,
        gene_id,
        attempts=0,
        max_attempts=6,
        is_won=False,
        is_finished=False,
        hint_used=False,
        points_earned=0,
    ):
        session = GameSession(
            user_id=user_id,
            gene_id=gene_id,
            attempts=attempts,
            max_attempts=max_attempts,
            is_won=is_won,
            is_finished=is_finished,
            hint_used=hint_used,
            points_earned=points_earned,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    return _create


@pytest_asyncio.fixture
async def make_prize_type(db):
    async def _create(
        name="discount_10",
        title="Скидка 10%",
        description="Скидка 10% на следующий заказ",
        prize_value="GENE10",
        is_active=True,
    ):
        prize = PrizeType(
            name=name,
            title=title,
            description=description,
            prize_value=prize_value,
            is_active=is_active,
        )
        db.add(prize)
        await db.commit()
        await db.refresh(prize)
        return prize

    return _create


# ---------------------------------------------------------------------------
# Convenience: готовые объекты
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def user(make_user):
    return await make_user()


@pytest_asyncio.fixture
async def gene(make_gene):
    return await make_gene(name="MTHFR")


@pytest_asyncio.fixture
async def gene_5(make_gene):
    """Ген из 5 букв — для тестов с вводом неверного слова."""
    return await make_gene(name="APOE4")