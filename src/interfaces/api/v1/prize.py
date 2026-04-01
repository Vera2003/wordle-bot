"""Prize API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.prize import (
    AwardPrizeCommand,
    AwardPrizeHandler,
    CreatePrizeCommand,
    CreatePrizeHandler,
    GetActivePrizesHandler,
    GetActivePrizesQuery,
    GetPrizeByIdHandler,
    GetPrizeByIdQuery,
    GetUnusedUserPrizesHandler,
    GetUnusedUserPrizesQuery,
    GetUserPrizesHandler,
    GetUserPrizesQuery,
    MarkPrizeAsUsedCommand,
    MarkPrizeAsUsedHandler,
    PrizeOutput,
    UserPrizeOutput,
)
from src.core.security import require_admin_api_key
from src.domain.prize import PrizeNotAvailableError, PrizeNotFoundError
from src.infrastructure.db.repositories.prize import PrizeRepositoryImpl, UserPrizeRepositoryImpl
from src.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/prizes", tags=["prizes"])


class MarkPrizeAsUsedInput(BaseModel):
    """Optional body for marking a user prize as used."""

    model_config = ConfigDict(extra="forbid")

    used_at: datetime | None = None


async def get_prize_repository(db: AsyncSession = Depends(get_db_session)) -> PrizeRepositoryImpl:
    """Dependency: get prize repository."""
    return PrizeRepositoryImpl(db)


async def get_user_prize_repository(
    db: AsyncSession = Depends(get_db_session),
) -> UserPrizeRepositoryImpl:
    """Dependency: get user prize repository."""
    return UserPrizeRepositoryImpl(db)


@router.get("/")
async def list_active_prizes(
    repository: PrizeRepositoryImpl = Depends(get_prize_repository),
) -> list[PrizeOutput]:
    """List active prize definitions."""
    handler = GetActivePrizesHandler(repository)
    return await handler(GetActivePrizesQuery())


@router.get("/users/{user_id}/unused")
async def get_unused_user_prizes(
    user_id: UUID,
    repository: UserPrizeRepositoryImpl = Depends(get_user_prize_repository),
) -> list[UserPrizeOutput]:
    """List unused prizes for a user."""
    try:
        handler = GetUnusedUserPrizesHandler(repository)
        return await handler(GetUnusedUserPrizesQuery(user_id=user_id))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/users/{user_id}")
async def get_user_prizes(
    user_id: UUID,
    used_only: bool = False,
    repository: UserPrizeRepositoryImpl = Depends(get_user_prize_repository),
) -> list[UserPrizeOutput]:
    """List prizes awarded to a user."""
    try:
        handler = GetUserPrizesHandler(repository)
        return await handler(GetUserPrizesQuery(user_id=user_id, used_only=used_only))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/{prize_id}")
async def get_prize(
    prize_id: UUID,
    repository: PrizeRepositoryImpl = Depends(get_prize_repository),
) -> PrizeOutput:
    """Get prize details by ID."""
    try:
        handler = GetPrizeByIdHandler(repository)
        return await handler(GetPrizeByIdQuery(prize_id=prize_id))
    except PrizeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prize not found") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_api_key)])
async def create_prize(
    command: CreatePrizeCommand,
    repository: PrizeRepositoryImpl = Depends(get_prize_repository),
) -> PrizeOutput:
    """Create a new prize definition."""
    try:
        handler = CreatePrizeHandler(repository)
        return await handler(command)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/award", dependencies=[Depends(require_admin_api_key)])
async def award_prize(
    command: AwardPrizeCommand,
    prize_repository: PrizeRepositoryImpl = Depends(get_prize_repository),
    user_prize_repository: UserPrizeRepositoryImpl = Depends(get_user_prize_repository),
) -> UserPrizeOutput:
    """Award a prize to a user."""
    try:
        handler = AwardPrizeHandler(prize_repository, user_prize_repository)
        return await handler(command)
    except PrizeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prize not found") from error
    except PrizeNotAvailableError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/user-prizes/{user_prize_id}/use", dependencies=[Depends(require_admin_api_key)])
async def mark_prize_as_used(
    user_prize_id: UUID,
    body: MarkPrizeAsUsedInput,
    repository: UserPrizeRepositoryImpl = Depends(get_user_prize_repository),
) -> UserPrizeOutput:
    """Mark an awarded prize as used."""
    try:
        handler = MarkPrizeAsUsedHandler(repository)
        return await handler(
            MarkPrizeAsUsedCommand(
                user_prize_id=user_prize_id,
                used_at=body.used_at,
            )
        )
    except PrizeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User prize not found") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error