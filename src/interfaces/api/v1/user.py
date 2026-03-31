"""User API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.user.commands import (
    AddPointsHandler,
    AddPointsCommand,
    GetOrCreateUserCommand,
    GetOrCreateUserHandler,
    GetOrCreateUserOutput,
    RestoreEnergyHandler,
    RestoreEnergyCommand,
    RestoreEnergyOutput,
    UseEnergyCommand,
    UseEnergyHandler,
    UseEnergyOutput,
)
from src.application.user.queries import (
    GetUserProfileHandler,
    GetUserProfileOutput,
    GetUserProfileQuery,
)
from src.application.user.dto import AddPointsInput
from src.domain.user.errors import UserNotFoundError
from src.infrastructure.db.repositories.user import UserRepositoryImpl
from src.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/users", tags=["users"])


async def get_user_repository(db: AsyncSession = Depends(get_db_session)) -> UserRepositoryImpl:
    """Dependency: Get user repository."""
    return UserRepositoryImpl(db)


@router.post("/get-or-create")
async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
    repository = Depends(get_user_repository),
) -> GetOrCreateUserOutput:
    """Get existing user or create new one."""
    try:
        handler = GetOrCreateUserHandler(repository)
        command = GetOrCreateUserCommand(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )
        return await handler(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}")
async def get_user_profile(
    user_id: UUID,
    repository = Depends(get_user_repository),
) -> GetUserProfileOutput:
    """Get user profile by ID."""
    try:
        handler = GetUserProfileHandler(repository)
        query = GetUserProfileQuery(user_id=user_id)
        return await handler(query)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{user_id}/points")
async def add_points(
    user_id: UUID,
    input_data: AddPointsInput,
    repository = Depends(get_user_repository),
):
    """Add points to user."""
    try:
        handler = AddPointsHandler(repository)
        command = AddPointsCommand(user_id=user_id, points=input_data.points)
        return await handler(command)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{user_id}/use-energy")
async def use_energy(
    user_id: UUID,
    repository = Depends(get_user_repository),
) -> UseEnergyOutput:
    """Use one energy point."""
    try:
        handler = UseEnergyHandler(repository)
        command = UseEnergyCommand(user_id=user_id)
        return await handler(command)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{user_id}/restore-energy")
async def restore_energy(
    user_id: UUID,
    repository = Depends(get_user_repository),
) -> RestoreEnergyOutput:
    """Restore energy to maximum."""
    try:
        handler = RestoreEnergyHandler(repository)
        command = RestoreEnergyCommand(user_id=user_id)
        return await handler(command)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
