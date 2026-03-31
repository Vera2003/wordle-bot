"""Stats domain services - pure business logic for calculate stats."""

from .value_objects import WinRate, GameStats, GlobalStats, UserStats, TopPlayer
from .errors import InvalidWinRateError


class StatsCalculator:
    """Pure domain service for calculating stats from raw numbers."""
    
    @staticmethod
    def calculate_win_rate(won_games: int, total_games: int) -> WinRate:
        """Calculate win rate percentage."""
        if total_games == 0:
            return WinRate(0.0)
        
        percentage = (won_games / total_games) * 100
        return WinRate(round(percentage, 2))
    
    @staticmethod
    def calculate_game_stats(
        total_games: int,
        won_games: int,
    ) -> GameStats:
        """Calculate complete game statistics."""
        lost_games = total_games - won_games
        win_rate = StatsCalculator.calculate_win_rate(won_games, total_games)
        
        return GameStats(
            total_games=total_games,
            won_games=won_games,
            lost_games=lost_games,
            win_rate=win_rate,
        )
    
    @staticmethod
    def create_global_stats(
        total_users: int,
        total_games: int,
        won_games: int,
        total_genes: int,
        active_genes: int,
        top_players: list[TopPlayer],
    ) -> GlobalStats:
        """Create global stats value object."""
        game_stats = StatsCalculator.calculate_game_stats(total_games, won_games)
        
        return GlobalStats(
            total_users=total_users,
            total_games=game_stats.total_games,
            won_games=game_stats.won_games,
            lost_games=game_stats.lost_games,
            win_rate=game_stats.win_rate,
            total_genes=total_genes,
            active_genes=active_genes,
            top_players=top_players,
        )
    
    @staticmethod
    def create_user_stats(
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        total_points: int,
        energy: int,
        total_games: int,
        won_games: int,
    ) -> UserStats:
        """Create user stats value object."""
        game_stats = StatsCalculator.calculate_game_stats(total_games, won_games)
        
        return UserStats(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            total_points=total_points,
            energy=energy,
            game_stats=game_stats,
        )
