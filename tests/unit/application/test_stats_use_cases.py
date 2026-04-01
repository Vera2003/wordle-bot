"""Unit tests for Stats application use cases."""

from unittest.mock import AsyncMock

import pytest

from src.application.stats.queries import (
    GetGlobalStatsHandler,
    GetGlobalStatsQuery,
    GetUserStatsHandler,
    GetUserStatsQuery,
)
from src.domain.stats import (
    GameStats,
    GlobalStats,
    TopPlayer,
    UserNotFoundError,
    UserStats,
    WinRate,
)


class TestGetGlobalStatsHandler:
    """Tests for GetGlobalStats query."""

    @pytest.mark.asyncio
    async def test_get_global_stats_success(self):
        """Test getting global stats successfully."""
        top_players = [
            TopPlayer(111111111, "Alice", 5000),
            TopPlayer(222222222, "Bob", 4500),
        ]

        global_stats = GlobalStats(
            total_users=100,
            total_games=500,
            won_games=250,
            lost_games=250,
            win_rate=WinRate(50.0),
            total_genes=50,
            active_genes=45,
            top_players=top_players,
        )

        repository = AsyncMock()
        repository.get_global_stats.return_value = global_stats

        handler = GetGlobalStatsHandler(repository)
        query = GetGlobalStatsQuery()

        result = await handler(query)

        assert result.total_users == 100
        assert result.total_games == 500
        assert result.won_games == 250
        assert result.lost_games == 250
        assert result.win_rate == 50.0
        assert result.total_genes == 50
        assert result.active_genes == 45
        assert len(result.top_players) == 2
        assert result.top_players[0].name == "Alice"
        assert result.top_players[0].points == 5000
        repository.get_global_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_global_stats_empty(self):
        """Test global stats with no data."""
        global_stats = GlobalStats(
            total_users=0,
            total_games=0,
            won_games=0,
            lost_games=0,
            win_rate=WinRate(0.0),
            total_genes=0,
            active_genes=0,
            top_players=[],
        )

        repository = AsyncMock()
        repository.get_global_stats.return_value = global_stats

        handler = GetGlobalStatsHandler(repository)
        query = GetGlobalStatsQuery()

        result = await handler(query)

        assert result.total_users == 0
        assert result.total_games == 0
        assert len(result.top_players) == 0


class TestGetUserStatsHandler:
    """Tests for GetUserStats query."""

    @pytest.mark.asyncio
    async def test_get_user_stats_success(self):
        """Test getting user stats successfully."""
        game_stats = GameStats(
            total_games=30,
            won_games=20,
            lost_games=10,
            win_rate=WinRate(66.67),
        )

        user_stats = UserStats(
            telegram_id=123456789,
            username="john_doe",
            full_name="John Doe",
            total_points=3000,
            energy=2,
            game_stats=game_stats,
        )

        repository = AsyncMock()
        repository.get_user_stats.return_value = user_stats

        handler = GetUserStatsHandler(repository)
        query = GetUserStatsQuery(telegram_id=123456789)

        result = await handler(query)

        assert result.telegram_id == 123456789
        assert result.username == "john_doe"
        assert result.full_name == "John Doe"
        assert result.total_points == 3000
        assert result.energy == 2
        assert result.game_stats.total_games == 30
        assert result.game_stats.won_games == 20
        assert result.game_stats.lost_games == 10
        assert result.game_stats.win_rate == 66.67
        repository.get_user_stats.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_get_user_stats_not_found(self):
        """Test getting user stats when user not found."""
        repository = AsyncMock()
        repository.get_user_stats.side_effect = UserNotFoundError("User not found")

        handler = GetUserStatsHandler(repository)
        query = GetUserStatsQuery(telegram_id=999999999)

        with pytest.raises(UserNotFoundError):
            await handler(query)

    @pytest.mark.asyncio
    async def test_get_user_stats_no_username(self):
        """Test user stats without username (only full_name)."""
        game_stats = GameStats(0, 0, 0, WinRate(0.0))

        user_stats = UserStats(
            telegram_id=123456789,
            username=None,
            full_name="Jane Doe",
            total_points=0,
            energy=5,
            game_stats=game_stats,
        )

        repository = AsyncMock()
        repository.get_user_stats.return_value = user_stats

        handler = GetUserStatsHandler(repository)
        query = GetUserStatsQuery(telegram_id=123456789)

        result = await handler(query)

        assert result.username is None
        assert result.full_name == "Jane Doe"
