"""API routes init."""

from .user import router as user_router
from .stats import router as stats_router

__all__ = [
    "user_router",
    "stats_router",
]
