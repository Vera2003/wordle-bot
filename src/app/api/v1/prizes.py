from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...db.session import get_db
from ...db.models.prize import PrizeType, UserPrize
from sqlalchemy import select

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_prizes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех призов"""
    result = await db.execute(
        select(Prize).offset(skip).limit(limit)
    )
    prizes = result.scalars().all()
    
    return [
        {
            "id": prize.id,
            "name": prize.name,
            "description": prize.description,
            "required_score": prize.required_score,
            "image_url": prize.image_url,
            "is_active": prize.is_active,
        }
        for prize in prizes
    ]


@router.get("/{prize_id}", response_model=dict)
async def get_prize(
    prize_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о конкретном призе"""
    result = await db.execute(
        select(Prize).where(Prize.id == prize_id)
    )
    prize = result.scalar_one_or_none()
    
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    
    return {
        "id": prize.id,
        "name": prize.name,
        "description": prize.description,
        "required_score": prize.required_score,
        "image_url": prize.image_url,
        "is_active": prize.is_active,
    }


@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_prizes(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить призы пользователя"""
    # TODO: Implement user prizes logic
    return []