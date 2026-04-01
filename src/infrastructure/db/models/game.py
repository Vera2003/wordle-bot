"""Game ORM model."""

import uuid
from datetime import datetime
from typing import List, Literal, Optional, TypedDict

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from ..base import Base

GuessStatus = Literal["correct", "present", "absent"]


class GuessLetterPayload(TypedDict):
    letter: str
    status: GuessStatus


class GuessResultPayload(TypedDict):
    letters: list[GuessLetterPayload]


class UUIDString(TypeDecorator[str]):
    """String-backed UUID column that accepts either UUID or string input."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value: str | uuid.UUID | None, dialect) -> str | None:
        del dialect
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        del dialect
        return value


class GameSessionModel(Base):
    """ORM Model: game_sessions table."""

    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(
        UUIDString(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUIDString(), ForeignKey("users.id"), nullable=False
    )
    word: Mapped[str] = mapped_column(String(50), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=6)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, default=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    attempts_history: Mapped[List["GameAttemptModel"]] = relationship(
        "GameAttemptModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class GameAttemptModel(Base):
    """ORM Model: game_attempts table."""

    __tablename__ = "game_attempts"

    id: Mapped[str] = mapped_column(
        UUIDString(), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUIDString(),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    guess_word: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[GuessResultPayload] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["GameSessionModel"] = relationship(
        "GameSessionModel",
        back_populates="attempts_history",
    )
