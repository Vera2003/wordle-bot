from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...db.session import get_db
from ...db.models.user import User
from ...db.models.game import GameSession
from ...db.models.gene import Gene

router = APIRouter()


@router.get("/global")
async def get_global_stats(db: AsyncSession = Depends(get_db)):
    """Глобальная статистика"""
    # Всего пользователей
    total_users = await db.scalar(select(func.count(User.id)))
    
    # Всего игр
    total_games = await db.scalar(
        select(func.count(GameSession.id)).where(GameSession.is_finished == True)
    )
    
    # Выигранных игр
    won_games = await db.scalar(
        select(func.count(GameSession.id)).where(GameSession.is_won == True)
    )
    
    # Всего генов
    total_genes = await db.scalar(select(func.count(Gene.id)))
    active_genes = await db.scalar(
        select(func.count(Gene.id)).where(Gene.is_active == True)
    )
    
    # Топ игроков
    top_query = (
        select(User.telegram_id, User.full_name, User.username, User.total_points)
        .order_by(User.total_points.desc())
        .limit(10)
    )
    result = await db.execute(top_query)
    top_players = [
        {
            "telegram_id": row.telegram_id,
            "name": row.full_name or row.username or "Аноним",
            "points": row.total_points
        }
        for row in result.all()
    ]
    
    win_rate = (won_games / total_games * 100) if total_games > 0 else 0
    
    return {
        "total_users": total_users,
        "total_games": total_games,
        "won_games": won_games,
        "lost_games": total_games - won_games,
        "win_rate": round(win_rate, 2),
        "total_genes": total_genes,
        "active_genes": active_genes,
        "top_players": top_players
    }


@router.get("/user/{telegram_id}")
async def get_user_stats(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Статистика конкретного пользователя"""
    # Получаем пользователя
    query = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return {"error": "Пользователь не найден"}
    
    # Статистика игр
    total_games = await db.scalar(
        select(func.count(GameSession.id)).where(
            GameSession.user_id == user.id,
            GameSession.is_finished == True
        )
    )
    
    won_games = await db.scalar(
        select(func.count(GameSession.id)).where(
            GameSession.user_id == user.id,
            GameSession.is_won == True
        )
    )
    
    win_rate = (won_games / total_games * 100) if total_games > 0 else 0
    
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "full_name": user.full_name,
        "total_points": user.total_points,
        "energy": user.energy,
        "total_games": total_games,
        "won_games": won_games,
        "lost_games": total_games - won_games,
        "win_rate": round(win_rate, 2)
    }
