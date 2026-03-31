"""Integration tests for User API routes."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.interfaces.main import create_app
from src.infrastructure.db.base import Base


@pytest.fixture
async def app_fixture():
    """Create FastAPI app with test database."""
    # Import models to register them with Base
    from src.infrastructure.db.models.user import UserModel  # noqa
    from src.infrastructure.db.models.game import GameSessionModel  # noqa
    
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
    
    yield app
    
    await engine.dispose()


@pytest.fixture
async def client(app_fixture):
    """Create async HTTP client."""
    transport = ASGITransport(app=app_fixture)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_or_create_user(client):
    """Test getting or creating user."""
    response = await client.post(
        "/api/v1/users/get-or-create?telegram_id=123&username=testuser&full_name=Test%20User"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_id"] == 123
    assert data["username"] == "testuser"
    assert data["full_name"] == "Test User"
    assert data["energy"] == 5
    assert data["total_points"] == 0


@pytest.mark.asyncio
async def test_get_or_create_user_invalid_telegram_id(client):
    """Test error when telegram_id is invalid."""
    response = await client.post(
        "/api/v1/users/get-or-create?telegram_id=0&username=testuser"
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_user_profile(client):
    """Test getting user profile."""
    # First create a user
    create_response = await client.post(
        "/api/v1/users/get-or-create?telegram_id=123&username=testuser"
    )
    user_data = create_response.json()
    user_id = user_data["user_id"]
    
    # Now get the profile
    response = await client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["telegram_id"] == 123


@pytest.mark.asyncio
async def test_get_user_profile_not_found(client):
    """Test error when user not found."""
    from uuid import uuid4
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/users/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_points(client):
    """Test adding points to user."""
    # Create a user
    create_response = await client.post(
        "/api/v1/users/get-or-create?telegram_id=123&username=testuser"
    )
    user_id = create_response.json()["user_id"]
    
    # Add points
    response = await client.post(
        f"/api/v1/users/{user_id}/points",
        json={"points": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_total_points"] == 10


@pytest.mark.asyncio
async def test_use_energy(client):
    """Test using energy."""
    # Create a user
    create_response = await client.post(
        "/api/v1/users/get-or-create?telegram_id=123&username=testuser"
    )
    user_id = create_response.json()["user_id"]
    initial_energy = create_response.json()["energy"]
    
    # Use energy
    response = await client.post(f"/api/v1/users/{user_id}/use-energy")
    assert response.status_code == 200
    data = response.json()
    assert data["remaining_energy"] == initial_energy - 1


@pytest.mark.asyncio
async def test_restore_energy(client):
    """Test restoring energy."""
    # Create a user
    create_response = await client.post(
        "/api/v1/users/get-or-create?telegram_id=123&username=testuser"
    )
    user_id = create_response.json()["user_id"]
    
    # Use energy first
    await client.post(f"/api/v1/users/{user_id}/use-energy")
    
    # Restore energy
    response = await client.post(f"/api/v1/users/{user_id}/restore-energy")
    assert response.status_code == 200
    data = response.json()
    assert data["current_energy"] == 5
