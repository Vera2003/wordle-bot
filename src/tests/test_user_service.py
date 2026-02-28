"""
Тесты UserService.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.user_service import UserService


class TestGetByTelegramId:

    @pytest.mark.asyncio
    async def test_returns_existing_user(self, db, user):
        svc = UserService(db)
        found = await svc.get_by_telegram_id(user.telegram_id)

        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self, db):
        svc = UserService(db)
        found = await svc.get_by_telegram_id(telegram_id=999_999)
        assert found is None

    @pytest.mark.asyncio
    async def test_returns_correct_user_among_many(self, db, make_user):
        u1 = await make_user(telegram_id=1)
        u2 = await make_user(telegram_id=2)

        svc = UserService(db)
        found = await svc.get_by_telegram_id(2)

        assert found is not None  # ← убеждает Pylance что дальше None быть не может
        assert found.id == u2.id
        assert found.id != u1.id


class TestGetOrCreate:

    @pytest.mark.asyncio
    async def test_creates_new_user(self, db):
        svc = UserService(db)
        user = await svc.get_or_create(
            telegram_id=42,
            username="newbie",
            full_name="New User",
        )

        assert user.id is not None
        assert user.telegram_id == 42
        assert user.username == "newbie"

    @pytest.mark.asyncio
    async def test_returns_existing_user(self, db, user):
        svc = UserService(db)
        found = await svc.get_or_create(
            telegram_id=user.telegram_id,
            username="other_name",
        )

        # Возвращает существующего, не создаёт нового
        assert found.id == user.id
        assert found.username == user.username  # имя не перезаписано

    @pytest.mark.asyncio
    async def test_new_user_gets_daily_energy(self, db):
        from src.app.core.config import settings
        svc = UserService(db)
        user = await svc.get_or_create(telegram_id=777)

        assert user.energy == settings.daily_energy

    @pytest.mark.asyncio
    async def test_accepts_none_username(self, db):
        svc = UserService(db)
        user = await svc.get_or_create(telegram_id=55, username=None)
        assert user.username is None


class TestUpdatePoints:

    @pytest.mark.asyncio
    async def test_adds_points(self, db, user):
        svc = UserService(db)
        await svc.update_points(user.id, points=100)

        await db.refresh(user)
        assert user.total_points == 100

    @pytest.mark.asyncio
    async def test_accumulates_points(self, db, make_user):
        user = await make_user(total_points=50)
        svc = UserService(db)

        await svc.update_points(user.id, points=30)

        await db.refresh(user)
        assert user.total_points == 80

    @pytest.mark.asyncio
    async def test_ignores_missing_user(self, db):
        svc = UserService(db)
        # Не должно бросать исключение
        await svc.update_points(user_id=999_999, points=100)
