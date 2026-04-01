"""Get user profile query."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.domain.user import Username, UserNotFoundError, UserRepository


def _username_value(username: Username | None) -> str | None:
    return username.value if username else None


class GetUserProfileQuery(BaseModel):
    """Query to get user profile."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class GetUserProfileOutput(BaseModel):
    """User profile information."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    telegram_id: int
    username: str | None
    full_name: str | None
    energy: int
    max_energy: int
    total_points: int
    created_at: datetime
    updated_at: datetime


class GetUserProfileHandler:
    """Handler for GetUserProfile query."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def __call__(self, query: GetUserProfileQuery) -> GetUserProfileOutput:
        """Execute query."""
        user = await self.user_repository.get_by_id(query.user_id)

        if not user:
            raise UserNotFoundError(f"User {query.user_id} not found")

        return GetUserProfileOutput(
            user_id=user.id,
            telegram_id=user.telegram_id.value,
            username=_username_value(user.username),
            full_name=user.full_name,
            energy=user.energy.value,
            max_energy=user.energy.max,
            total_points=user.total_points,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
