from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class AchievementType(Base):
    """Типы достижений"""
    
    __tablename__ = "achievement_types"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reward_value: Mapped[str] = mapped_column(String(100), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        back_populates="achievement_type",
        cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    """Достижения пользователей"""
    
    __tablename__ = "user_achievements"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    achievement_type_id: Mapped[int] = mapped_column(
        ForeignKey("achievement_types.id"),
        nullable=False
    )
    
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="achievements")
    achievement_type: Mapped["AchievementType"] = relationship(
        back_populates="user_achievements"
    )
