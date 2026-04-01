"""Integration tests for LLM API routes."""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.llm import LLMLogModel
from src.interfaces.api.v1.llm import get_llm_service
from src.interfaces.main import create_app


class FakeLLMService:
    """Deterministic stand-in for ProxyAPI-backed service."""

    async def generate_gene_fact(
        self, gene_name: str, gene_description: str, user_id=None
    ):
        del gene_description, user_id

        class Result:
            text = f"Fact about {gene_name}"
            is_fallback = False
            latency_ms = 42

        return Result()

    async def answer_genetics_question(self, question: str, history, user_id=None):
        del history, user_id

        class Result:
            text = f"Answer to {question}"
            is_fallback = False
            latency_ms = 55

        return Result()


@pytest.fixture
async def app_fixture(monkeypatch):
    """Create FastAPI app with test database and llm fixtures."""
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("PROXYAPI_KEY", "dummy-key")
    monkeypatch.setenv("PROXYAPI_MODEL", "gpt-4o-mini")
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
    app.dependency_overrides[get_llm_service] = lambda: FakeLLMService()

    async with session_maker() as session:
        session.add_all(
            [
                LLMLogModel(
                    id=uuid4(),
                    request_type="fact",
                    model="gpt-4o-mini",
                    prompt="Fact prompt",
                    response="Fact response",
                    is_fallback=False,
                    latency_ms=120,
                    error=None,
                    created_at=datetime(2026, 3, 31, 12, 0, 0),
                ),
                LLMLogModel(
                    id=uuid4(),
                    request_type="chat",
                    model="gpt-4o-mini",
                    prompt="Chat prompt",
                    response="Fallback response",
                    is_fallback=True,
                    latency_ms=250,
                    error="timeout",
                    created_at=datetime(2026, 3, 31, 12, 5, 0),
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
async def test_generate_gene_fact(client):
    """Fact generation runs through the migrated llm route."""
    response = await client.post(
        "/api/v1/llm/fact",
        json={
            "gene_name": "APOE",
            "gene_description": "A gene involved in lipid transport and metabolism.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["gene_name"] == "APOE"
    assert data["fact"] == "Fact about APOE"
    assert data["is_fallback"] is False


@pytest.mark.asyncio
async def test_chat_genetics(client):
    """Chat generation runs through the migrated llm route."""
    response = await client.post(
        "/api/v1/llm/chat",
        json={
            "question": "What is a gene?",
            "history": [{"role": "user", "text": "Hi"}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is a gene?"
    assert data["answer"] == "Answer to What is a gene?"


@pytest.mark.asyncio
async def test_get_llm_logs_requires_admin_key(client):
    """Admin key is required for llm log inspection."""
    response = await client.get("/api/v1/llm/logs")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_llm_logs_with_filters(client):
    """Admin log listing supports request type and fallback filters."""
    response = await client.get(
        "/api/v1/llm/logs?request_type=chat&fallback_only=true",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["request_type"] == "chat"
    assert data["items"][0]["is_fallback"] is True


@pytest.mark.asyncio
async def test_get_llm_stats(client):
    """Admin llm stats are aggregated from persisted logs."""
    response = await client.get(
        "/api/v1/llm/stats",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 2
    assert data["fallback_count"] == 1
    assert data["fallback_rate"] == 50.0
    assert data["requests_by_type"] == {"fact": 1, "chat": 1}
