"""
Тесты GeneOfDayService.

Проверяем: кэш, инвалидацию, выбор только активных генов,
поведение при деактивированном гене в кэше.
"""
import pytest

from src.app.services.gene_of_day_service import GeneOfDayService


class TestGet:

    @pytest.mark.asyncio
    async def test_returns_active_gene(self, db, gene, redis):
        svc = GeneOfDayService(db, redis)
        result = await svc.get()

        assert result.id == gene.id
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_caches_gene_id_in_redis(self, db, gene, redis):
        svc = GeneOfDayService(db, redis)
        await svc.get()

        key = svc._cache_key()
        assert key in redis._store
        assert redis._store[key] == str(gene.id)

    @pytest.mark.asyncio
    async def test_returns_cached_gene_on_second_call(self, db, gene, redis):
        svc = GeneOfDayService(db, redis)
        first = await svc.get()
        second = await svc.get()

        assert first.id == second.id
        # set вызвался только один раз — второй раз из кэша
        assert redis.set.call_count == 1

    @pytest.mark.asyncio
    async def test_raises_when_no_active_genes(self, db, redis):
        svc = GeneOfDayService(db, redis)
        with pytest.raises(ValueError, match="нет активных генов"):
            await svc.get()

    @pytest.mark.asyncio
    async def test_skips_inactive_gene_in_cache(self, db, make_gene, redis):
        """Если кэшированный ген деактивировали — выбирается другой."""
        inactive = await make_gene(name="APOE4", is_active=False)
        active   = await make_gene(name="MTHFR", is_active=True)

        # Вручную кладём в кэш id деактивированного гена
        svc = GeneOfDayService(db, redis)
        redis._store[svc._cache_key()] = str(inactive.id)

        result = await svc.get()

        assert result.id == active.id
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_only_active_genes_are_chosen(self, db, make_gene, redis):
        await make_gene(name="INACT", is_active=False)
        active = await make_gene(name="ACTIV", is_active=True)

        svc = GeneOfDayService(db, redis)
        result = await svc.get()

        assert result.id == active.id


class TestInvalidate:

    @pytest.mark.asyncio
    async def test_removes_cache_key(self, db, gene, redis):
        svc = GeneOfDayService(db, redis)
        await svc.get()                 # создаём кэш
        assert svc._cache_key() in redis._store

        await svc.invalidate()
        assert svc._cache_key() not in redis._store

    @pytest.mark.asyncio
    async def test_invalidate_then_get_picks_new_gene(self, db, make_gene, redis):
        """После инвалидации сервис выбирает ген заново."""
        gene = await make_gene(name="MTHFR")
        svc = GeneOfDayService(db, redis)

        await svc.get()
        await svc.invalidate()
        result = await svc.get()

        assert result.id == gene.id  # единственный ген, поэтому тот же
        assert redis.set.call_count == 2  # set вызван дважды
