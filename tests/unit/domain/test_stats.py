"""Unit tests for Stats domain."""

import pytest

from src.domain.stats import (
    GameStats,
    GlobalStats,
    StatsCalculator,
    TopPlayer,
    UserStats,
    WinRate,
)


class TestWinRate:
    """Tests for WinRate value object."""

    def test_creation_valid(self):
        """Test creating valid win rate."""
        wr = WinRate(50.0)
        assert wr.value == 50.0

    def test_creation_minimum(self):
        """Test creating minimum win rate (0)."""
        wr = WinRate(0.0)
        assert wr.value == 0.0

    def test_creation_maximum(self):
        """Test creating maximum win rate (100)."""
        wr = WinRate(100.0)
        assert wr.value == 100.0

    def test_creation_negative_raises(self):
        """Test creating negative win rate raises error."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            WinRate(-1.0)

    def test_creation_over_100_raises(self):
        """Test creating win rate over 100 raises error."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            WinRate(101.0)

    def test_frozen(self):
        """Test WinRate is immutable."""
        wr = WinRate(50.0)
        with pytest.raises(AttributeError):
            wr.value = 75.0


class TestGameStats:
    """Tests for GameStats value object."""

    def test_creation_valid(self):
        """Test creating valid game stats."""
        wr = WinRate(50.0)
        stats = GameStats(
            total_games=10,
            won_games=5,
            lost_games=5,
            win_rate=wr,
        )
        assert stats.total_games == 10
        assert stats.won_games == 5
        assert stats.lost_games == 5

    def test_creation_no_games(self):
        """Test creating stats with zero games."""
        wr = WinRate(0.0)
        stats = GameStats(
            total_games=0,
            won_games=0,
            lost_games=0,
            win_rate=wr,
        )
        assert stats.total_games == 0

    def test_creation_invariant_violation_sum(self):
        """Test won + lost must equal total."""
        wr = WinRate(50.0)
        with pytest.raises(ValueError, match="Won \\+ lost games must equal total"):
            GameStats(
                total_games=10,
                won_games=6,
                lost_games=5,  # Should be 4
                win_rate=wr,
            )

    def test_creation_negative_total_raises(self):
        """Test negative total games raises error."""
        wr = WinRate(0.0)
        with pytest.raises(ValueError, match="Total games cannot be negative"):
            GameStats(
                total_games=-1,
                won_games=0,
                lost_games=0,
                win_rate=wr,
            )


class TestTopPlayer:
    """Tests for TopPlayer value object."""

    def test_creation_valid(self):
        """Test creating valid top player."""
        player = TopPlayer(
            telegram_id=123456789,
            name="John Doe",
            points=5000,
        )
        assert player.telegram_id == 123456789
        assert player.name == "John Doe"
        assert player.points == 5000

    def test_creation_invalid_telegram_id(self):
        """Test invalid telegram ID."""
        with pytest.raises(ValueError, match="Telegram ID must be positive"):
            TopPlayer(
                telegram_id=-1,
                name="John",
                points=100,
            )

    def test_creation_invalid_points(self):
        """Test negative points."""
        with pytest.raises(ValueError, match="Points cannot be negative"):
            TopPlayer(
                telegram_id=123456789,
                name="John",
                points=-10,
            )

    def test_creation_empty_name(self):
        """Test empty name."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            TopPlayer(
                telegram_id=123456789,
                name="",
                points=100,
            )


class TestGlobalStats:
    """Tests for GlobalStats value object."""

    def test_creation_valid(self):
        """Test creating valid global stats."""
        wr = WinRate(50.0)
        top_player = TopPlayer(123456789, "Jane", 1000)

        stats = GlobalStats(
            total_users=100,
            total_games=500,
            won_games=250,
            lost_games=250,
            win_rate=wr,
            total_genes=50,
            active_genes=45,
            top_players=[top_player],
        )

        assert stats.total_users == 100
        assert stats.total_genes == 50
        assert len(stats.top_players) == 1

    def test_creation_invalid_genes(self):
        """Test active genes > total genes raises error."""
        wr = WinRate(50.0)
        with pytest.raises(ValueError, match="Active genes cannot exceed total"):
            GlobalStats(
                total_users=100,
                total_games=500,
                won_games=250,
                lost_games=250,
                win_rate=wr,
                total_genes=50,
                active_genes=51,  # Over total
                top_players=[],
            )


class TestUserStats:
    """Tests for UserStats value object."""

    def test_creation_valid(self):
        """Test creating valid user stats."""
        wr = WinRate(75.0)
        game_stats = GameStats(
            total_games=20,
            won_games=15,
            lost_games=5,
            win_rate=wr,
        )

        stats = UserStats(
            telegram_id=123456789,
            username="john_doe",
            full_name="John Doe",
            total_points=2500,
            energy=3,
            game_stats=game_stats,
        )

        assert stats.telegram_id == 123456789
        assert stats.username == "john_doe"
        assert stats.total_points == 2500
        assert stats.game_stats.won_games == 15

    def test_creation_no_username(self):
        """Test creating user stats without username."""
        wr = WinRate(0.0)
        game_stats = GameStats(0, 0, 0, wr)

        stats = UserStats(
            telegram_id=123456789,
            username=None,
            full_name="John Doe",
            total_points=0,
            energy=5,
            game_stats=game_stats,
        )

        assert stats.username is None
        assert stats.full_name == "John Doe"


class TestStatsCalculator:
    """Tests for StatsCalculator service."""

    def test_calculate_win_rate_50_percent(self):
        """Test calculating 50% win rate."""
        wr = StatsCalculator.calculate_win_rate(5, 10)
        assert wr.value == 50.0

    def test_calculate_win_rate_100_percent(self):
        """Test calculating 100% win rate."""
        wr = StatsCalculator.calculate_win_rate(10, 10)
        assert wr.value == 100.0

    def test_calculate_win_rate_0_percent(self):
        """Test calculating 0% win rate."""
        wr = StatsCalculator.calculate_win_rate(0, 10)
        assert wr.value == 0.0

    def test_calculate_win_rate_no_games(self):
        """Test calculating win rate with no games (returns 0%)."""
        wr = StatsCalculator.calculate_win_rate(0, 0)
        assert wr.value == 0.0

    def test_calculate_win_rate_rounding(self):
        """Test win rate rounding to 2 decimal places."""
        wr = StatsCalculator.calculate_win_rate(1, 3)
        assert wr.value == 33.33

    def test_calculate_game_stats(self):
        """Test calculating complete game stats."""
        stats = StatsCalculator.calculate_game_stats(10, 7)

        assert stats.total_games == 10
        assert stats.won_games == 7
        assert stats.lost_games == 3
        assert stats.win_rate.value == 70.0

    def test_create_global_stats(self):
        """Test creating global stats."""
        top_players = [
            TopPlayer(111111111, "Alice", 5000),
            TopPlayer(222222222, "Bob", 4500),
        ]

        stats = StatsCalculator.create_global_stats(
            total_users=100,
            total_games=500,
            won_games=250,
            total_genes=50,
            active_genes=45,
            top_players=top_players,
        )

        assert stats.total_users == 100
        assert stats.total_games == 500
        assert stats.won_games == 250
        assert stats.lost_games == 250
        assert stats.win_rate.value == 50.0
        assert len(stats.top_players) == 2
        assert stats.total_genes == 50
        assert stats.active_genes == 45

    def test_create_user_stats(self):
        """Test creating user stats."""
        stats = StatsCalculator.create_user_stats(
            telegram_id=123456789,
            username="john_doe",
            full_name="John Doe",
            total_points=3000,
            energy=2,
            total_games=30,
            won_games=15,
        )

        assert stats.telegram_id == 123456789
        assert stats.username == "john_doe"
        assert stats.full_name == "John Doe"
        assert stats.total_points == 3000
        assert stats.energy == 2
        assert stats.game_stats.total_games == 30
        assert stats.game_stats.won_games == 15
        assert stats.game_stats.lost_games == 15
        assert stats.game_stats.win_rate.value == 50.0
