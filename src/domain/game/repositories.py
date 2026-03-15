"""Game repository abstractions (ports)."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import GameSession


class GameRepository(ABC):
    """
    Port: repository for GameSession persistence.
    
    This interface defines how GameSession can be saved and loaded.
    Implementation is in infrastructure layer (SQLAlchemy).
    """
    
    @abstractmethod
    async def save(self, game: GameSession) -> None:
        """Save a game session (create or update)."""
        pass
    
    @abstractmethod
    async def get_by_id(self, game_id: UUID) -> Optional[GameSession]:
        """Get game session by ID."""
        pass
    
    @abstractmethod
    async def get_active_by_user(self, user_id: UUID) -> Optional[GameSession]:
        """Get active (not finished) game for a user."""
        pass
    
    @abstractmethod
    async def delete(self, game_id: UUID) -> None:
        """Delete a game session."""
        pass
