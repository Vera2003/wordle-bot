"""Stats query handlers (read-only operations)."""

from pydantic import BaseModel, ConfigDict, Field

from src.domain.stats import StatsRepository, UserNotFoundError
from src.application.stats.dto import GlobalStatsOutput, GameStatsOutput, TopPlayerOutput, UserStatsOutput


class GetGlobalStatsQuery(BaseModel):
    """Query to get global system statistics."""
    
    model_config = ConfigDict(extra="forbid")
    
    # No parameters needed for global stats


class GetGlobalStatsHandler:
    """Handler for GetGlobalStats query."""
    
    def __init__(self, stats_repository: StatsRepository):
        self.stats_repository = stats_repository
    
    async def __call__(self, query: GetGlobalStatsQuery) -> GlobalStatsOutput:
        """Execute query to fetch global statistics."""
        stats = await self.stats_repository.get_global_stats()
        
        top_players = [
            TopPlayerOutput(
                telegram_id=player.telegram_id,
                name=player.name,
                points=player.points,
            )
            for player in stats.top_players
        ]
        
        return GlobalStatsOutput(
            total_users=stats.total_users,
            total_games=stats.total_games,
            won_games=stats.won_games,
            lost_games=stats.lost_games,
            win_rate=stats.win_rate.value,
            total_genes=stats.total_genes,
            active_genes=stats.active_genes,
            top_players=top_players,
        )


class GetUserStatsQuery(BaseModel):
    """Query to get statistics for a specific user."""
    
    model_config = ConfigDict(extra="forbid")
    
    telegram_id: int = Field(..., gt=0, description="User's Telegram ID")


class GetUserStatsHandler:
    """Handler for GetUserStats query."""
    
    def __init__(self, stats_repository: StatsRepository):
        self.stats_repository = stats_repository
    
    async def __call__(self, query: GetUserStatsQuery) -> UserStatsOutput:
        """Execute query to fetch user statistics."""
        try:
            stats = await self.stats_repository.get_user_stats(query.telegram_id)
        except UserNotFoundError:
            raise UserNotFoundError(f"User with telegram_id {query.telegram_id} not found")
        
        return UserStatsOutput(
            telegram_id=stats.telegram_id,
            username=stats.username,
            full_name=stats.full_name,
            total_points=stats.total_points,
            energy=stats.energy,
            game_stats=GameStatsOutput(
                total_games=stats.game_stats.total_games,
                won_games=stats.game_stats.won_games,
                lost_games=stats.game_stats.lost_games,
                win_rate=stats.game_stats.win_rate.value,
            ),
        )
