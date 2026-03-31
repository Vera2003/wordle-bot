"""Achievement ORM models."""

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class AchievementTypeModel(Base):
    """ORM model for achievement definitions."""

    __tablename__ = "achievement_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reward_value: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user_achievements: Mapped[list["UserAchievementModel"]] = relationship(
        back_populates="achievement_type",
        cascade="all, delete-orphan",
    )


class UserAchievementModel(Base):
    """ORM model for achievements unlocked by users."""

    __tablename__ = "user_achievements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    achievement_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("achievement_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    achievement_type: Mapped[AchievementTypeModel] = relationship(back_populates="user_achievements")
