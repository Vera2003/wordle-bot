"""Stats domain module."""

from .value_objects import (
    WinRate,
    GameStats,
    GlobalStats,
    UserStats,
    TopPlayer,
)
from .services import StatsCalculator
from .repositories import StatsRepository
from .errors import (
    StatsError,
    UserNotFoundError,
    InvalidWinRateError,
)

__all__ = [
    "WinRate",
    "GameStats",
    "GlobalStats",
    "UserStats",
    "TopPlayer",
    "StatsCalculator",
    "StatsRepository",
    "StatsError",
    "UserNotFoundError",
    "InvalidWinRateError",
]
