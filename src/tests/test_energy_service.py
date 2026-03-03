"""
Тесты EnergyService.

Покрываем: кэш Redis, трату, пополнение, восстановление,
авто-восстановление при смене дня.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.energy_service import EnergyService


class TestGetUserEnergy:

    @pytest.mark.asyncio
    async def test_returns_user_energy_from_db(self, db, user, redis):
        svc = EnergyService(db, redis)
        energy = await svc.get_user_energy(user.id)
        assert energy == user.energy

    @pytest.mark.asyncio
    async def test_caches_result_in_redis(self, db, user, redis):
        svc = EnergyService(db, redis)
        await svc.get_user_energy(user.id)

        cache_key = svc._cache_key(user.id)
        assert cache_key in redis._store

    @pytest.mark.asyncio
    async def test_reads_from_cache_on_second_call(self, db, user, redis):
        svc = EnergyService(db, redis)
        await svc.get_user_energy(user.id)

        # Подмениваем кэш вручную
        redis._store[svc._cache_key(user.id)] = "99"
        energy = await svc.get_user_energy(user.id)
        assert energy == 99

    @pytest.mark.asyncio
    async def test_returns_zero_for_missing_user(self, db, redis):
        svc = EnergyService(db, redis)
        energy = await svc.get_user_energy(user_id=999_999)
        assert energy == 0

    @pytest.mark.asyncio
    async def test_auto_restore_when_day_changed(self, db, make_user, redis):
        """Если last_energy_reset вчера — энергия должна восстановиться."""
        yesterday = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        user = await make_user(energy=0)
        user.last_energy_reset = yesterday
        await db.commit()

        svc = EnergyService(db, redis)
        energy = await svc.get_user_energy(user.id)

        # После авто-восстановления энергия = daily_energy (6 по умолчанию)
        assert energy > 0


class TestSpendEnergy:

    @pytest.mark.asyncio
    async def test_deducts_energy(self, db, make_user, redis):
        user = await make_user(energy=6)
        svc = EnergyService(db, redis)

        success = await svc.spend_energy(user.id, amount=2)

        assert success is True
        await db.refresh(user)
        assert user.energy == 4

    @pytest.mark.asyncio
    async def test_returns_false_when_not_enough(self, db, make_user, redis):
        user = await make_user(energy=1)
        svc = EnergyService(db, redis)

        success = await svc.spend_energy(user.id, amount=2)

        assert success is False
        await db.refresh(user)
        assert user.energy == 1  # не изменилась

    @pytest.mark.asyncio
    async def test_updates_cache_after_spend(self, db, make_user, redis):
        user = await make_user(energy=6)
        svc = EnergyService(db, redis)

        await svc.spend_energy(user.id, amount=2)

        cached = redis._store.get(svc._cache_key(user.id))
        assert cached == "4"

    @pytest.mark.asyncio
    async def test_spend_exact_amount_succeeds(self, db, make_user, redis):
        user = await make_user(energy=3)
        svc = EnergyService(db, redis)

        success = await svc.spend_energy(user.id, amount=3)

        assert success is True
        await db.refresh(user)
        assert user.energy == 0

    @pytest.mark.asyncio
    async def test_returns_false_for_missing_user(self, db, redis):
        svc = EnergyService(db, redis)
        success = await svc.spend_energy(user_id=999_999, amount=1)
        assert success is False


class TestAddEnergy:

    @pytest.mark.asyncio
    async def test_adds_energy(self, db, make_user, redis):
        user = await make_user(energy=3)
        svc = EnergyService(db, redis)

        await svc.add_energy(user.id, amount=2)

        await db.refresh(user)
        assert user.energy == 5

    @pytest.mark.asyncio
    async def test_updates_cache_after_add(self, db, make_user, redis):
        user = await make_user(energy=3)
        svc = EnergyService(db, redis)

        await svc.add_energy(user.id, amount=2)

        cached = redis._store.get(svc._cache_key(user.id))
        assert cached == "5"

    @pytest.mark.asyncio
    async def test_ignores_missing_user(self, db, redis):
        svc = EnergyService(db, redis)
        # Не должно бросать исключение
        await svc.add_energy(user_id=999_999, amount=5)


class TestRestoreDailyEnergy:

    @pytest.mark.asyncio
    async def test_restores_to_daily_limit(self, db, make_user, redis):
        user = await make_user(energy=0)
        svc = EnergyService(db, redis)

        await svc.restore_daily_energy(user.id)

        await db.refresh(user)
        from src.app.core.config import get_settings
        settings = get_settings()
        assert user.energy == settings.daily_energy

    @pytest.mark.asyncio
    async def test_updates_last_reset_timestamp(self, db, make_user, redis):
        old_reset = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
        user = await make_user()
        user.last_energy_reset = old_reset
        await db.commit()

        svc = EnergyService(db, redis)
        await svc.restore_daily_energy(user.id)

        await db.refresh(user)
        assert user.last_energy_reset > old_reset

    @pytest.mark.asyncio
    async def test_updates_cache_after_restore(self, db, make_user, redis):
        user = await make_user(energy=0)
        svc = EnergyService(db, redis)

        await svc.restore_daily_energy(user.id)

        from src.app.core.config import get_settings
        settings = get_settings()
        cached = redis._store.get(svc._cache_key(user.id))
        assert cached == str(settings.daily_energy)
