"""
Тесты StatsService.
"""
import pytest

from src.app.services.stats_service import StatsService


class TestGetGlobal:

    @pytest.mark.asyncio
    async def test_empty_db(self, db):
        svc = StatsService(db)
        stats = await svc.get_global()

        assert stats["total_users"] == 0
        assert stats["total_games"] == 0
        assert stats["won_games"] == 0
        assert stats["win_rate"] == 0
        assert stats["top_players"] == []

    @pytest.mark.asyncio
    async def test_counts_users(self, db, make_user):
        await make_user(telegram_id=1)
        await make_user(telegram_id=2)

        svc = StatsService(db)
        stats = await svc.get_global()

        assert stats["total_users"] == 2

    @pytest.mark.asyncio
    async def test_counts_finished_games(self, db, user, gene, make_game_session):
        await make_game_session(user_id=user.id, gene_id=gene.id, is_finished=True, is_won=True)
        await make_game_session(user_id=user.id, gene_id=gene.id, is_finished=True, is_won=False)
        await make_game_session(user_id=user.id, gene_id=gene.id, is_finished=False)  # не считается

        svc = StatsService(db)
        stats = await svc.get_global()

        assert stats["total_games"] == 2
        assert stats["won_games"] == 1
        assert stats["lost_games"] == 1

    @pytest.mark.asyncio
    async def test_win_rate(self, db, user, make_gene, make_game_session):
        g1 = await make_gene(name="GENE1")
        g2 = await make_gene(name="GENE2")
        await make_game_session(user_id=user.id, gene_id=g1.id, is_finished=True, is_won=True)
        await make_game_session(user_id=user.id, gene_id=g2.id, is_finished=True, is_won=False)

        svc = StatsService(db)
        stats = await svc.get_global()

        assert stats["win_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_counts_genes(self, db, make_gene):
        await make_gene(name="GENE1", is_active=True)
        await make_gene(name="GENE2", is_active=True)
        await make_gene(name="GENE3", is_active=False)

        svc = StatsService(db)
        stats = await svc.get_global()

        assert stats["total_genes"] == 3
        assert stats["active_genes"] == 2

    @pytest.mark.asyncio
    async def test_top_players_sorted_by_points(self, db, make_user):
        u1 = await make_user(telegram_id=1, total_points=100)
        u2 = await make_user(telegram_id=2, total_points=500)
        u3 = await make_user(telegram_id=3, total_points=250)

        svc = StatsService(db)
        stats = await svc.get_global()

        points = [p["points"] for p in stats["top_players"]]
        assert points == sorted(points, reverse=True)
        assert points[0] == 500


class TestGetForUser:

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_user(self, db):
        svc = StatsService(db)
        result = await svc.get_for_user(telegram_id=999_999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_user_data(self, db, user):
        svc = StatsService(db)
        result = await svc.get_for_user(user.telegram_id)

        assert result["telegram_id"] == user.telegram_id
        assert "total_games" in result
        assert "win_rate" in result

    @pytest.mark.asyncio
    async def test_counts_only_this_user_games(self, db, make_user, gene, make_game_session):
        u1 = await make_user(telegram_id=1)
        u2 = await make_user(telegram_id=2)

        await make_game_session(user_id=u1.id, gene_id=gene.id, is_finished=True, is_won=True)
        await make_game_session(user_id=u2.id, gene_id=gene.id, is_finished=True, is_won=True)
        await make_game_session(user_id=u2.id, gene_id=gene.id, is_finished=True, is_won=False)

        svc = StatsService(db)
        stats_u1 = await svc.get_for_user(u1.telegram_id)
        stats_u2 = await svc.get_for_user(u2.telegram_id)

        assert stats_u1["total_games"] == 1
        assert stats_u2["total_games"] == 2
