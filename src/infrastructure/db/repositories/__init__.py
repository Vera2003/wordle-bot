"""Database repositories - implementations of domain repository interfaces."""

from .game import SQLAlchemyGameRepository

__all__ = ["SQLAlchemyGameRepository"]
