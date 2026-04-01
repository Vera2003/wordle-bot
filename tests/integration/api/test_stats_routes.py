"""Integration tests for Stats API routes."""

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.infrastructure.db.base import Base
from src.infrastructure.db.models.game import GameSessionModel
from src.infrastructure.db.models.user import UserModel
from src.interfaces.main import create_app


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
async def app_with_users_fixture():
    """Create FastAPI app with test database and sample data."""
    # Create in-memory SQLite engine for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    app = create_app()
    app.state.db_session_maker = session_maker

    # Add sample data
    async with session_maker() as session:
        # Create users
        user1 = UserModel(telegram_id=100, username="user1", energy=5, total_points=50)
        user2 = UserModel(telegram_id=200, username="user2", energy=3, total_points=30)
        session.add(user1)
        session.add(user2)
        await session.flush()

        # Create games
        game1 = GameSessionModel(
            user_id=user1.id,
            word="python",
            attempts_count=3,
            is_finished=True,
            is_won=True,
            points_earned=10,
            finished_at=_utc_now(),
        )
        game2 = GameSessionModel(
            user_id=user1.id,
            word="hello",
            attempts_count=6,
            is_finished=True,
            is_won=False,
            points_earned=0,
            finished_at=_utc_now(),
        )
        game3 = GameSessionModel(
            user_id=user2.id,
            word="world",
            attempts_count=4,
            is_finished=True,
            is_won=True,
            points_earned=10,
            finished_at=_utc_now(),
        )
        session.add(game1)
        session.add(game2)
        session.add(game3)

        await session.commit()

    yield app

    await engine.dispose()


@pytest.fixture
async def client(app_with_users_fixture):
    """Create async HTTP client."""
    transport = ASGITransport(app=app_with_users_fixture)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_global_stats(client):
    """Test getting global statistics."""
    response = await client.get("/api/v1/stats/global")
    assert response.status_code == 200
    data = response.json()

    assert data["total_users"] == 2
    assert data["total_games"] == 3
    assert data["won_games"] == 2
    assert data["lost_games"] == 1
    assert 50 < data["win_rate"] < 70  # ~66%
    assert data["total_genes"] == 0


@pytest.mark.asyncio
async def test_get_user_stats(client):
    """Test getting user statistics."""
    response = await client.get("/api/v1/stats/user/100")
    assert response.status_code == 200
    data = response.json()

    assert data["telegram_id"] == 100
    assert data["username"] == "user1"
    assert data["game_stats"]["total_games"] == 2
    assert data["game_stats"]["won_games"] == 1
    assert data["game_stats"]["lost_games"] == 1


@pytest.mark.asyncio
async def test_get_user_stats_not_found(client):
    """Test error when user not found."""
    response = await client.get("/api/v1/stats/user/999")
    assert response.status_code == 404
