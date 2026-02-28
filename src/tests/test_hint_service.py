"""
Тесты HintService.

Покрываем лимит подсказок, блокировку после завершённой игры,
содержимое первой и второй подсказок.
"""
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.hint_service import HintService


@pytest.fixture
def hint_svc(db, redis):
    return HintService(db, redis)


class TestShowHint:

    @pytest.mark.asyncio
    async def test_first_hint_succeeds(self, db, redis, user, gene):
        """Первая подсказка возвращается без ошибок."""
        # Кладём ген в кэш GeneOfDayService
        from src.app.services.gene_of_day_service import GeneOfDayService
        svc_god = GeneOfDayService(db, redis)
        redis._store[svc_god._cache_key()] = str(gene.id)

        svc = HintService(db, redis)
        result = await svc.show_hint(user.id)

        assert result["success"] is True
        assert result["hint_number"] == 1
        assert "text" in result

    @pytest.mark.asyncio
    async def test_first_hint_shows_length_and_difficulty(self, db, redis, user, gene):
        from src.app.services.gene_of_day_service import GeneOfDayService
        redis._store[GeneOfDayService(db, redis)._cache_key()] = str(gene.id)

        svc = HintService(db, redis)
        result = await svc.show_hint(user.id)

        assert str(len(gene.name)) in result["text"]

    @pytest.mark.asyncio
    async def test_second_hint_shows_gene_hint_text(self, db, redis, user, gene):
        from src.app.services.gene_of_day_service import GeneOfDayService
        redis._store[GeneOfDayService(db, redis)._cache_key()] = str(gene.id)

        svc = HintService(db, redis)
        await svc.show_hint(user.id)          # 1-я подсказка
        result = await svc.show_hint(user.id)  # 2-я подсказка

        assert result["success"] is True
        assert result["hint_number"] == 2
        assert gene.hint in result["text"]

    @pytest.mark.asyncio
    async def test_third_hint_exceeds_daily_limit(self, db, redis, user, gene):
        from src.app.services.gene_of_day_service import GeneOfDayService
        redis._store[GeneOfDayService(db, redis)._cache_key()] = str(gene.id)

        svc = HintService(db, redis)
        await svc.show_hint(user.id)   # 1-я
        await svc.show_hint(user.id)   # 2-я
        result = await svc.show_hint(user.id)  # 3-я — лимит

        assert result["success"] is False
        assert result["error"] == "daily_limit"

    @pytest.mark.asyncio
    async def test_hint_blocked_after_finished_game(
        self, db, redis, user, gene, make_game_session
    ):
        """Если игра завершена сегодня — подсказки недоступны."""
        from src.app.services.gene_of_day_service import GeneOfDayService
        redis._store[GeneOfDayService(db, redis)._cache_key()] = str(gene.id)

        await make_game_session(
            user_id=user.id,
            gene_id=gene.id,
            is_finished=True,
            is_won=True,
        )

        svc = HintService(db, redis)
        result = await svc.show_hint(user.id)

        assert result["success"] is False
        assert result["error"] == "game_finished"

    @pytest.mark.asyncio
    async def test_hint_increments_counter(self, db, redis, user, gene):
        from src.app.services.gene_of_day_service import GeneOfDayService
        redis._store[GeneOfDayService(db, redis)._cache_key()] = str(gene.id)

        svc = HintService(db, redis)
        assert await svc.get_daily_hint_count(user.id) == 0

        await svc.show_hint(user.id)
        assert await svc.get_daily_hint_count(user.id) == 1

        await svc.show_hint(user.id)
        assert await svc.get_daily_hint_count(user.id) == 2
