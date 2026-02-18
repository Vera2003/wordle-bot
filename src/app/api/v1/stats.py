from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...services.stats_service import StatsService

router = APIRouter()


@router.get("/global")
async def get_global_stats(db: AsyncSession = Depends(get_db)):
    service = StatsService(db)
    return await service.get_global()


@router.get("/user/{telegram_id}")
async def get_user_stats(telegram_id: int, db: AsyncSession = Depends(get_db)):
    service = StatsService(db)
    return await service.get_for_user(telegram_id)
