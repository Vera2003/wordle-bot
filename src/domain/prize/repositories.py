"""Prize repository interface (domain contract)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import Prize, UserPrize


class PrizeRepository(ABC):
    """
    Port: Repository interface for Prize aggregate root.
    
    Defines what data operations the domain needs for Prize entities.
    Implementation lives in infrastructure layer (SQLAlchemy adapter).
    """
    
    @abstractmethod
    async def save(self, prize: Prize) -> None:
        """Store prize definition."""
        pass
    
    @abstractmethod
    async def get_by_id(self, prize_id: UUID) -> Optional[Prize]:
        """Retrieve prize by ID."""
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Prize]:
        """Find prize by unique name."""
        pass
    
    @abstractmethod
    async def get_active_prizes(self) -> list[Prize]:
        """
        Get all active prizes available for award.
        
        Useful for: showing prize catalog, random selection.
        """
        pass
    
    @abstractmethod
    async def delete(self, prize_id: UUID) -> None:
        """Remove prize definition."""
        pass


class UserPrizeRepository(ABC):
    """
    Port: Repository for UserPrize (earned prize instances).
    
    Each UserPrize record links a User to a Prize they've earned.
    """
    
    @abstractmethod
    async def save(self, user_prize: UserPrize) -> None:
        """Track that user earned a prize."""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_prize_id: UUID) -> Optional[UserPrize]:
        """Retrieve specific user prize record."""
        pass
    
    @abstractmethod
    async def get_user_prizes(self, user_id: UUID, used_only: bool = False) -> list[UserPrize]:
        """
        Get all prizes earned by user, optionally filtered by used status.
        
        Args:
            user_id: User to query
            used_only: If True, return only used/claimed prizes.
                      If False, return all (used + unused).
        """
        pass
    
    @abstractmethod
    async def get_unused_prizes(self, user_id: UUID) -> list[UserPrize]:
        """Get all unclaimed prizes for user."""
        pass
    
    @abstractmethod
    async def delete(self, user_prize_id: UUID) -> None:
        """Remove prize from user's collection (rare)."""
        pass
