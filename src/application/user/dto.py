"""User application layer data transfer objects."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserProfileOutput(BaseModel):
    """User profile information for API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    telegram_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    energy: int
    max_energy: int
    total_points: int
    created_at: datetime
    updated_at: datetime


class AddPointsInput(BaseModel):
    """Input for adding points to user."""
    
    model_config = ConfigDict(extra="forbid")
    
    points: int = Field(..., gt=0, description="Points to add")


class AddPointsOutput(BaseModel):
    """Output after adding points."""
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    new_total_points: int


class UseEnergyInput(BaseModel):
    """Input for using energy."""
    
    model_config = ConfigDict(extra="forbid")
    
    user_id: UUID


class UseEnergyOutput(BaseModel):
    """Output after using energy."""
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    remaining_energy: int


class RestoreEnergyOutput(BaseModel):
    """Output after restoring energy."""
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    current_energy: int
