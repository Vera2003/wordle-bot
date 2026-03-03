from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import require_admin_api_key
from ...db.models.user import User
from ...db.session import get_db
from ...schemas.user import UserResponse, UserListResponse

router = APIRouter(dependencies=[Depends(require_admin_api_key)])


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Получить список всех пользователей."""
    total: int = await db.scalar(select(func.count(User.id))) or 0

    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return UserListResponse(
        total=total,
        items=[UserResponse.model_validate(u) for u in users],
    )


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить пользователя по Telegram ID."""
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь {telegram_id} не найден",
        )
    return user


@router.delete("/{telegram_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Удалить пользователя и все его данные (каскадно)."""
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь {telegram_id} не найден",
        )
    await db.delete(user)
    await db.commit()