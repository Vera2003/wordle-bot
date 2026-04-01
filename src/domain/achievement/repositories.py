"""Achievement repository interface (domain contract)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import AchievementType, UserAchievement


class AchievementTypeRepository(ABC):
    """
    Port: Repository interface for AchievementType aggregate root.

    Defines what data operations the domain needs for achievement definitions.
    Implementation lives in infrastructure layer (SQLAlchemy adapter).
    """

    @abstractmethod
    async def save(self, achievement_type: AchievementType) -> None:
        """Store achievement definition."""
        pass

    @abstractmethod
    async def get_by_id(self, achievement_id: UUID) -> Optional[AchievementType]:
        """Retrieve achievement type by ID."""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[AchievementType]:
        """Find achievement by unique name."""
        pass

    @abstractmethod
    async def get_all(self) -> list[AchievementType]:
        """Get all defined achievements."""
        pass

    @abstractmethod
    async def delete(self, achievement_id: UUID) -> None:
        """Remove achievement definition."""
        pass


class UserAchievementRepository(ABC):
    """
    Port: Repository for UserAchievement (unlocked achievement instances).

    Each UserAchievement record links a User to an AchievementType they've unlocked.
    """

    @abstractmethod
    async def save(self, user_achievement: UserAchievement) -> None:
        """Record that user unlocked an achievement."""
        pass

    @abstractmethod
    async def get_by_id(self, user_achievement_id: UUID) -> Optional[UserAchievement]:
        """Retrieve specific user achievement record."""
        pass

    @abstractmethod
    async def get_by_user_and_achievement(
        self,
        user_id: UUID,
        achievement_type_id: UUID,
    ) -> Optional[UserAchievement]:
        """
        Check if user already has this achievement.

        Used to prevent double-unlock and track achievement status.
        """
        pass

    @abstractmethod
    async def get_user_achievements(self, user_id: UUID) -> list[UserAchievement]:
        """Get all achievements unlocked by user."""
        pass

    @abstractmethod
    async def delete(self, user_achievement_id: UUID) -> None:
        """Remove achievement from user (rare, admin only)."""
        pass
