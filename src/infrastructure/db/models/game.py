"""SQLAlchemy models for Game aggregate."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID

from ..base import Base

if TYPE_CHECKING:
    from .user import User


class GameSessionModel(Base):
    """ORM Model: GameSession table"""
    
    __tablename__ = "game_sessions"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    gene_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("genes.id"), nullable=True)
    
    # Game state
    target_word: Mapped[str] = mapped_column(String(50), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=6)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, default=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    attempts_history: Mapped[List["GameAttemptModel"]] = relationship(
        "GameAttemptModel",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return (
            f"<GameSessionModel(id={self.id}, user_id={self.user_id}, "
            f"is_won={self.is_won})>"
        )


class GameAttemptModel(Base):
    """ORM Model: GameAttempt table"""
    
    __tablename__ = "game_attempts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("game_sessions.id", ondelete="CASCADE")
    )
    
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    guess_word: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    session: Mapped["GameSessionModel"] = relationship(
        "GameSessionModel",
        back_populates="attempts_history"
    )
    
    def __repr__(self) -> str:
        return (
            f"<GameAttemptModel(id={self.id}, session_id={self.session_id}, "
            f"attempt={self.attempt_number})>"
        )
