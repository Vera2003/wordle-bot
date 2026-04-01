"""User infrastructure layer - ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class UserModel(Base):
    """SQLAlchemy ORM model for User."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    energy: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_energy_reset: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships: lazy-loaded to avoid circular imports
    # These are defined in GameSessionModel.__init_subclass__

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, telegram_id={self.telegram_id}, points={self.total_points})>"
