"""
Сервис статистики.

До рефакторинга одинаковые SQL-запросы дублировались в:
- src/app/bot/handlers/admin.py (show_global_stats)
- src/app/api/v1/stats.py (get_global_stats, get_user_stats)
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.game import GameSession
from ..db.models.gene import Gene
from ..db.models.user import User


class StatsService:
    """Агрегирует статистику из БД. Используется и ботом, и REST API."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_global(self) -> dict:
        """Глобальная статистика по всем пользователям и играм."""
        total_users = await self.db.scalar(select(func.count(User.id))) or 0
        total_games = await self.db.scalar(
            select(func.count(GameSession.id)).where(GameSession.is_finished == True)
        ) or 0
        won_games = await self.db.scalar(
            select(func.count(GameSession.id)).where(GameSession.is_won == True)
        ) or 0
        total_genes = await self.db.scalar(select(func.count(Gene.id))) or 0
        active_genes = await self.db.scalar(
            select(func.count(Gene.id)).where(Gene.is_active == True)
        ) or 0

        top_result = await self.db.execute(
            select(User.telegram_id, User.full_name, User.username, User.total_points)
            .order_by(User.total_points.desc())
            .limit(10)
        )
        top_players = [
            {
                "telegram_id": row.telegram_id,
                "name": row.full_name or row.username or "Аноним",
                "points": row.total_points,
            }
            for row in top_result.all()
        ]

        win_rate = (won_games / total_games * 100) if total_games else 0

        return {
            "total_users": total_users,
            "total_games": total_games,
            "won_games": won_games,
            "lost_games": total_games - won_games,
            "win_rate": round(win_rate, 2),
            "total_genes": total_genes,
            "active_genes": active_genes,
            "top_players": top_players,
        }

    async def get_for_user(self, telegram_id: int) -> dict:
        """Статистика конкретного пользователя."""
        user = await self.db.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return {"error": "Пользователь не найден"}

        total_games = await self.db.scalar(
            select(func.count(GameSession.id)).where(
                GameSession.user_id == user.id,
                GameSession.is_finished == True,
            )
        ) or 0
        won_games = await self.db.scalar(
            select(func.count(GameSession.id)).where(
                GameSession.user_id == user.id,
                GameSession.is_won == True,
            )
        ) or 0

        win_rate = (won_games / total_games * 100) if total_games else 0

        return {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "full_name": user.full_name,
            "total_points": user.total_points,
            "energy": user.energy,
            "total_games": total_games,
            "won_games": won_games,
            "lost_games": total_games - won_games,
            "win_rate": round(win_rate, 2),
        }