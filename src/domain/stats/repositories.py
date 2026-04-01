"""Stats repository abstractions (ports)."""

from abc import ABC, abstractmethod

from .value_objects import GlobalStats, UserStats


class StatsRepository(ABC):
    """
    Port: repository for Stats queries (read-only).

    This interface defines how to query aggregated statistics.
    Implementation is in infrastructure layer (SQLAlchemy queries).
    """

    @abstractmethod
    async def get_global_stats(self) -> GlobalStats:
        """Get global statistics for entire system."""
        pass

    @abstractmethod
    async def get_user_stats(self, telegram_id: int) -> UserStats:
        """Get statistics for a specific user."""
        pass
