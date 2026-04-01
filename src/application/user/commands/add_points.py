"""Add points to user command."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.user import UserNotFoundError, UserRepository


class AddPointsCommand(BaseModel):
    """Command to add points to user."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    points: int = Field(..., gt=0, description="Points to add")


class AddPointsOutput(BaseModel):
    """Output after adding points."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    points_added: int
    new_total_points: int


class AddPointsHandler:
    """Handler for AddPoints command."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def __call__(self, command: AddPointsCommand) -> AddPointsOutput:
        """Execute command."""
        user = await self.user_repository.get_by_id(command.user_id)

        if not user:
            raise UserNotFoundError(f"User {command.user_id} not found")

        user.add_points(command.points)
        await self.user_repository.save(user)

        return AddPointsOutput(
            user_id=user.id,
            points_added=command.points,
            new_total_points=user.total_points,
        )
