"""Restore energy command."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.domain.user import UserNotFoundError, UserRepository


class RestoreEnergyCommand(BaseModel):
    """Command to restore user's energy to maximum."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class RestoreEnergyOutput(BaseModel):
    """Output after restoring energy."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    current_energy: int
    max_energy: int


class RestoreEnergyHandler:
    """Handler for RestoreEnergy command."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def __call__(self, command: RestoreEnergyCommand) -> RestoreEnergyOutput:
        """Execute command."""
        user = await self.user_repository.get_by_id(command.user_id)

        if not user:
            raise UserNotFoundError(f"User {command.user_id} not found")

        user.restore_energy()
        await self.user_repository.save(user)

        return RestoreEnergyOutput(
            user_id=user.id,
            current_energy=user.energy.value,
            max_energy=user.energy.max,
        )
