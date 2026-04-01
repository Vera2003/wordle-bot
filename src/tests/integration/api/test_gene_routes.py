"""Integration tests for Gene API routes."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.gene import GeneModel
from src.interfaces.main import create_app


@pytest.fixture
async def app_fixture(monkeypatch):
    """Create FastAPI app with test database and gene fixtures."""
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
        session.add_all(
            [
                GeneModel(
                    id=uuid4(),
                    name="APOE",
                    description="Apolipoprotein E.",
                    hint="Lipid transport gene.",
                    difficulty="easy",
                    is_active=True,
                ),
                GeneModel(
                    id=uuid4(),
                    name="MTHFR",
                    description="Folate metabolism gene.",
                    hint="Methylation support.",
                    difficulty="medium",
                    is_active=False,
                ),
            ]
        )
        await session.commit()

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
async def test_list_active_genes_returns_only_active(client):
    """Only active genes are listed by the migrated API."""
    response = await client.get("/api/v1/genes/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "APOE"
    assert data[0]["is_active"] is True


@pytest.mark.asyncio
async def test_get_random_gene_returns_active_gene(client):
    """Random gene endpoint returns an active gene."""
    response = await client.get("/api/v1/genes/random")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "APOE"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_gene_requires_admin_key(client):
    """Gene writes remain admin-protected."""
    response = await client.post(
        "/api/v1/genes/",
        json={
            "name": "BRCA",
            "description": "DNA repair gene.",
            "hint": "Cancer risk marker.",
            "difficulty": "hard",
            "is_active": True,
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_and_deactivate_gene(client):
    """Admins can create and deactivate genes through the new API."""
    create_response = await client.post(
        "/api/v1/genes/",
        headers={"X-Admin-API-Key": "test-admin-key"},
        json={
            "name": "BRCA",
            "description": "DNA repair gene.",
            "hint": "Cancer risk marker.",
            "difficulty": "hard",
            "is_active": True,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()

    get_response = await client.get(f"/api/v1/genes/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "BRCA"

    delete_response = await client.delete(
        f"/api/v1/genes/{created['id']}",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )
    assert delete_response.status_code == 204

    list_response = await client.get("/api/v1/genes/")
    names = [item["name"] for item in list_response.json()]
    assert "BRCA" not in names
