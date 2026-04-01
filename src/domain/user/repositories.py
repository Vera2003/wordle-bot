"""User repository abstractions (ports)."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import User
from .value_objects import TelegramId


class UserRepository(ABC):
    """
    Port: repository for User persistence.

    This interface defines how User can be saved and loaded.
    Implementation is in infrastructure layer (SQLAlchemy).
    """

    @abstractmethod
    async def save(self, user: User) -> None:
        """Save a user (create or update)."""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: TelegramId) -> Optional[User]:
        """Get user by Telegram ID."""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """Delete a user."""
        pass
