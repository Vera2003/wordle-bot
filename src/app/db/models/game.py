from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Boolean, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, List

from ..base import Base

if TYPE_CHECKING:
    from .user import User
    from .gene import Gene
    
class GameSession(Base):
    """Игровая сессия"""
    
    __tablename__ = "game_sessions"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    gene_id: Mapped[int] = mapped_column(Integer, ForeignKey("genes.id"))
    
    # Игровой процесс
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=6)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, default=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    
    # Временные метки
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="game_sessions")
    gene: Mapped["Gene"] = relationship("Gene", back_populates="game_sessions")
    attempts_history: Mapped[List["GameAttempt"]] = relationship(
        "GameAttempt",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return (
            f"<GameSession(id={self.id}, user_id={self.user_id}, "
            f"gene_id={self.gene_id}, is_won={self.is_won})>"
        )


class GameAttempt(Base):
    """Попытка угадывания"""
    
    __tablename__ = "game_attempts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("game_sessions.id", ondelete="CASCADE")
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    guess_word: Mapped[str] = mapped_column(String(10), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Связи
    session: Mapped["GameSession"] = relationship("GameSession", back_populates="attempts_history")
    
    def __repr__(self) -> str:
        return (
            f"<GameAttempt(id={self.id}, session_id={self.session_id}, "
            f"attempt={self.attempt_number}, word={self.guess_word})>"
        )