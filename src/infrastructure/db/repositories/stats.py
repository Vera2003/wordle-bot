"""Stats repository implementation."""

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.stats import (
    GlobalStats,
    StatsCalculator,
    StatsRepository,
    TopPlayer,
    UserNotFoundError,
    UserStats,
)
from src.infrastructure.db.models.game import GameSessionModel
from src.infrastructure.db.models.gene import GeneModel
from src.infrastructure.db.models.user import UserModel


class StatsRepositoryImpl(StatsRepository):
    """SQLAlchemy implementation of StatsRepository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_global_stats(self) -> GlobalStats:
        """Get global statistics for entire system."""
        # Count total users
        total_users = await self.session.scalar(select(func.count(UserModel.id))) or 0
        
        # Count total games (finished) and wins
        total_games = await self.session.scalar(
            select(func.count(GameSessionModel.id)).where(GameSessionModel.is_finished.is_(True))
        ) or 0
        
        won_games = await self.session.scalar(
            select(func.count(GameSessionModel.id)).where(GameSessionModel.is_won.is_(True))
        ) or 0
        
        # Count genes
        total_genes = await self.session.scalar(select(func.count(GeneModel.id))) or 0
        
        active_genes = await self.session.scalar(
            select(func.count(GeneModel.id)).where(GeneModel.is_active.is_(True))
        ) or 0
        
        # Get top 10 players
        top_result = await self.session.execute(
            select(UserModel.telegram_id, UserModel.full_name, UserModel.username, UserModel.total_points)
            .order_by(UserModel.total_points.desc())
            .limit(10)
        )
        
        top_players = [
            TopPlayer(
                telegram_id=row.telegram_id,
                name=row.full_name or row.username or "Аноним",
                points=row.total_points,
            )
            for row in top_result.all()
        ]
        
        # Use domain service to calculate stats
        return StatsCalculator.create_global_stats(
            total_users=total_users,
            total_games=total_games,
            won_games=won_games,
            total_genes=total_genes,
            active_genes=active_genes,
            top_players=top_players,
        )
    
    async def get_user_stats(self, telegram_id: int) -> UserStats:
        """Get statistics for a specific user."""
        # Get user
        user = await self.session.scalar(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        
        if not user:
            raise UserNotFoundError(f"User {telegram_id} not found")
        
        # Count user's games and wins
        total_games = await self.session.scalar(
            select(func.count(GameSessionModel.id)).where(
                GameSessionModel.user_id == str(user.id),
                GameSessionModel.is_finished.is_(True),
            )
        ) or 0
        
        won_games = await self.session.scalar(
            select(func.count(GameSessionModel.id)).where(
                GameSessionModel.user_id == str(user.id),
                GameSessionModel.is_won.is_(True),
            )
        ) or 0
        
        # Use domain service to calculate stats
        return StatsCalculator.create_user_stats(
            telegram_id=user.telegram_id,
            username=user.username,
            full_name=user.full_name,
            total_points=user.total_points,
            energy=user.energy,
            total_games=total_games,
            won_games=won_games,
        )
