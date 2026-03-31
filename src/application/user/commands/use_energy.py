"""Use energy command."""

from pydantic import BaseModel, ConfigDict
from uuid import UUID

from src.domain.user import UserRepository, UserNotFoundError


class UseEnergyCommand(BaseModel):
    """Command to use one energy point."""
    
    model_config = ConfigDict(extra="forbid")
    
    user_id: UUID


class UseEnergyOutput(BaseModel):
    """Output after using energy."""
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    remaining_energy: int
    is_depleted: bool


class UseEnergyHandler:
    """Handler for UseEnergy command."""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def __call__(self, command: UseEnergyCommand) -> UseEnergyOutput:
        """Execute command."""
        user = await self.user_repository.get_by_id(command.user_id)
        
        if not user:
            raise UserNotFoundError(f"User {command.user_id} not found")
        
        user.use_energy()
        await self.user_repository.save(user)
        
        return UseEnergyOutput(
            user_id=user.id,
            remaining_energy=user.energy.value,
            is_depleted=user.energy.is_depleted(),
        )
