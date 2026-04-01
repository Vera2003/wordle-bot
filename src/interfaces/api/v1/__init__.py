"""API routes init."""

from .gene import router as gene_router
from .llm import router as llm_router
from .prize import router as prize_router
from .user import router as user_router
from .stats import router as stats_router

__all__ = [
    "gene_router",
    "llm_router",
    "prize_router",
    "user_router",
    "stats_router",
]
