"""
REST API: управление призами.

Исправлен баг: в оригинале использовался неопределённый `Prize` вместо `PrizeType`.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models.prize import PrizeType, UserPrize
from ...db.session import get_db

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_prizes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Список всех типов призов."""
    result = await db.execute(select(PrizeType).offset(skip).limit(limit))
    prizes = result.scalars().all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "title": p.title,
            "description": p.description,
            "prize_value": p.prize_value,
            "is_active": p.is_active,
        }
        for p in prizes
    ]


@router.get("/{prize_id}", response_model=dict)
async def get_prize(prize_id: int, db: AsyncSession = Depends(get_db)):
    """Информация о конкретном призе."""
    prize = await db.get(PrizeType, prize_id)
    if not prize:
        raise HTTPException(status_code=404, detail="Приз не найден")

    return {
        "id": prize.id,
        "name": prize.name,
        "title": prize.title,
        "description": prize.description,
        "prize_value": prize.prize_value,
        "is_active": prize.is_active,
    }


@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_prizes(user_id: int, db: AsyncSession = Depends(get_db)):
    """Призы конкретного пользователя."""
    result = await db.execute(
        select(UserPrize).where(UserPrize.user_id == user_id)
    )
    user_prizes = result.scalars().all()

    return [
        {
            "id": up.id,
            "prize_type_id": up.prize_type_id,
            "is_used": up.is_used,
            "awarded_at": up.awarded_at.isoformat(),
            "used_at": up.used_at.isoformat() if up.used_at else None,
        }
        for up in user_prizes
    ]