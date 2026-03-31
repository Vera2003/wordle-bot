"""Stats API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.session import get_db_session
from src.infrastructure.db.repositories.stats import StatsRepositoryImpl
from src.application.stats.queries import (
    GetGlobalStatsHandler,
    GetGlobalStatsQuery,
    GetUserStatsHandler,
    GetUserStatsQuery,
)
from src.application.stats.dto import GlobalStatsOutput, UserStatsOutput
from src.domain.stats.errors import UserNotFoundError

router = APIRouter(prefix="/stats", tags=["stats"])


async def get_stats_repository(db: AsyncSession = Depends(get_db_session)) -> StatsRepositoryImpl:
    """Dependency: Get stats repository."""
    return StatsRepositoryImpl(db)


@router.get("/global")
async def get_global_stats(
    repository = Depends(get_stats_repository),
) -> GlobalStatsOutput:
    """Get global system statistics."""
    try:
        handler = GetGlobalStatsHandler(repository)
        query = GetGlobalStatsQuery()
        return await handler(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{telegram_id}")
async def get_user_stats(
    telegram_id: int,
    repository = Depends(get_stats_repository),
) -> UserStatsOutput:
    """Get statistics for a specific user."""
    try:
        handler = GetUserStatsHandler(repository)
        query = GetUserStatsQuery(telegram_id=telegram_id)
        return await handler(query)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
