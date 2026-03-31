"""GetOrCreate user command."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.user import User, TelegramId, Username, UserRepository


def _username_value(username: Username | None) -> str | None:
    return username.value if username else None


class GetOrCreateUserCommand(BaseModel):
    """Command to get existing user or create new one."""
    
    model_config = ConfigDict(extra="forbid")
    
    telegram_id: int = Field(..., gt=0)
    username: str | None = Field(None, max_length=32)
    full_name: str | None = Field(None, max_length=128)


class GetOrCreateUserOutput(BaseModel):
    """Output after get or create user."""
    
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
    is_new: bool  # True if user was just created


class GetOrCreateUserHandler:
    """Handler for GetOrCreateUser command."""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def __call__(self, command: GetOrCreateUserCommand) -> GetOrCreateUserOutput:
        """Execute command."""
        from uuid import uuid4
        
        telegram_id = TelegramId(command.telegram_id)
        
        # Try to get existing user
        existing_user = await self.user_repository.get_by_telegram_id(telegram_id)
        
        if existing_user:
            # User exists - update profile if needed
            if command.username or command.full_name:
                username = Username(command.username) if command.username else existing_user.username
                existing_user.update_profile(
                    username=username,
                    full_name=command.full_name or existing_user.full_name,
                )
                await self.user_repository.save(existing_user)
            
            return GetOrCreateUserOutput(
                user_id=existing_user.id,
                telegram_id=existing_user.telegram_id.value,
                username=_username_value(existing_user.username),
                full_name=existing_user.full_name,
                energy=existing_user.energy.value,
                max_energy=existing_user.energy.max,
                total_points=existing_user.total_points,
                created_at=existing_user.created_at,
                updated_at=existing_user.updated_at,
                is_new=False,
            )
        
        # Create new user
        new_user = User(
            id=uuid4(),
            telegram_id=telegram_id,
            username=Username(command.username) if command.username else Username(None),
            full_name=command.full_name,
        )
        
        await self.user_repository.save(new_user)
        
        return GetOrCreateUserOutput(
            user_id=new_user.id,
            telegram_id=new_user.telegram_id.value,
            username=_username_value(new_user.username),
            full_name=new_user.full_name,
            energy=new_user.energy.value,
            max_energy=new_user.energy.max,
            total_points=new_user.total_points,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
            is_new=True,
        )
