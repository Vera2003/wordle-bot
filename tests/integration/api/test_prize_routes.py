"""Integration tests for Prize API routes."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.prize import PrizeModel
from src.infrastructure.db.models.user import UserModel
from src.interfaces.main import create_app


@pytest.fixture
async def app_fixture(monkeypatch):
    """Create FastAPI app with test database and prize fixtures."""
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()
    app.state.db_session_maker = session_maker

    async with session_maker() as session:
        user = UserModel(
            id=uuid4(),
            telegram_id=100500,
            username="prize-user",
            full_name="Prize User",
            energy=5,
            total_points=10,
        )
        active_prize = PrizeModel(
            id=uuid4(),
            name="discount_10",
            title="10% Discount",
            description="Discount for a future purchase.",
            prize_value="GENE10",
            is_active=True,
        )
        inactive_prize = PrizeModel(
            id=uuid4(),
            name="hidden_badge",
            title="Hidden Badge",
            description="Secret profile badge.",
            prize_value="hidden",
            is_active=False,
        )
        session.add_all([user, active_prize, inactive_prize])
        await session.commit()

        app.state.test_user_id = str(user.id)
        app.state.active_prize_id = str(active_prize.id)

    yield app

    get_settings.cache_clear()
    await engine.dispose()


@pytest.fixture
async def client(app_fixture):
    """Create async HTTP client."""
    transport = ASGITransport(app=app_fixture)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_active_prizes_returns_only_active(client):
    """Only active prizes are listed by the migrated API."""
    response = await client.get("/api/v1/prizes/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "discount_10"
    assert data[0]["is_active"] is True


@pytest.mark.asyncio
async def test_create_prize_requires_admin_key(client):
    """Prize creation remains admin-protected."""
    response = await client.post(
        "/api/v1/prizes/",
        json={
            "name": "premium_badge",
            "title": "Premium Badge",
            "description": "Permanent profile badge.",
            "value": "premium",
            "is_active": True,
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_award_and_use_prize_flow(client, app_fixture):
    """Prize award and use flow works through the migrated API."""
    award_response = await client.post(
        "/api/v1/prizes/award",
        headers={"X-Admin-API-Key": "test-admin-key"},
        json={
            "user_id": app_fixture.state.test_user_id,
            "prize_id": app_fixture.state.active_prize_id,
        },
    )

    assert award_response.status_code == 200
    awarded = award_response.json()
    assert awarded["user_id"] == app_fixture.state.test_user_id
    assert awarded["prize_id"] == app_fixture.state.active_prize_id
    assert awarded["is_used"] is False

    user_prizes_response = await client.get(
        f"/api/v1/prizes/users/{app_fixture.state.test_user_id}"
    )
    assert user_prizes_response.status_code == 200
    assert len(user_prizes_response.json()) == 1

    unused_response = await client.get(
        f"/api/v1/prizes/users/{app_fixture.state.test_user_id}/unused"
    )
    assert unused_response.status_code == 200
    assert len(unused_response.json()) == 1

    use_response = await client.post(
        f"/api/v1/prizes/user-prizes/{awarded['id']}/use",
        headers={"X-Admin-API-Key": "test-admin-key"},
        json={},
    )
    assert use_response.status_code == 200
    assert use_response.json()["is_used"] is True

    used_only_response = await client.get(
        f"/api/v1/prizes/users/{app_fixture.state.test_user_id}?used_only=true"
    )
    assert used_only_response.status_code == 200
    assert len(used_only_response.json()) == 1
    assert used_only_response.json()[0]["is_used"] is True

    unused_after_response = await client.get(
        f"/api/v1/prizes/users/{app_fixture.state.test_user_id}/unused"
    )
    assert unused_after_response.status_code == 200
    assert unused_after_response.json() == []
