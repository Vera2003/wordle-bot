"""User domain entity."""

from __future__ import annotations

from typing import Optional
from datetime import datetime
from uuid import UUID
import uuid

from .value_objects import TelegramId, Username, Energy
from .errors import (
    InvalidTelegramIdError,
    InvalidUsernameError,
)


class User:
    """
    Aggregate Root: User entity.
    
    Represents a Telegram user in the system.
    """
    
    def __init__(
        self,
        id: UUID,
        telegram_id: TelegramId,
        username: Optional[Username] = None,
        full_name: Optional[str] = None,
        energy: Optional[Energy] = None,
        total_points: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if total_points < 0:
            raise ValueError("Total points cannot be negative")
        
        self.id = id
        self._telegram_id = telegram_id
        self._username = username or Username(None)
        self._full_name = full_name
        self._energy = energy or Energy(5)  # Default: 5 energy
        self._total_points = total_points
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @property
    def telegram_id(self) -> TelegramId:
        return self._telegram_id
    
    @property
    def username(self) -> Optional[Username]:
        return self._username
    
    @property
    def full_name(self) -> Optional[str]:
        return self._full_name
    
    @property
    def energy(self) -> Energy:
        return self._energy
    
    @property
    def total_points(self) -> int:
        return self._total_points
    
    def add_points(self, points: int) -> None:
        """Add points to user's total."""
        if points < 0:
            raise ValueError("Points cannot be negative")
        self._total_points += points
        self.updated_at = datetime.now()
    
    def use_energy(self) -> None:
        """Use one energy point for a game."""
        if self._energy.is_depleted():
            raise ValueError("No energy left to play")
        self._energy = self._energy.use_energy()
        self.updated_at = datetime.now()
    
    def restore_energy(self) -> None:
        """Restore energy to maximum."""
        self._energy = Energy(self._energy.max, self._energy.max)
        self.updated_at = datetime.now()
    
    def update_profile(
        self,
        username: Optional[Username] = None,
        full_name: Optional[str] = None,
    ) -> None:
        """Update user's profile information."""
        if username is not None:
            self._username = username
        if full_name is not None:
            self._full_name = full_name
        self.updated_at = datetime.now()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __repr__(self) -> str:
        return (
            f"User(id={self.id}, telegram_id={self._telegram_id.value}, "
            f"points={self._total_points}, energy={self._energy.value})"
        )
