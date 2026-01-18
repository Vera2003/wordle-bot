from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from ..base import Base


class User(Base):
    """Модель пользователя"""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Энергия
    energy: Mapped[int] = mapped_column(Integer, default=5)
    last_energy_reset: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Очки
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Связи
    game_sessions: Mapped[List["GameSession"]] = relationship(
        "GameSession", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    achievements: Mapped[List["UserAchievement"]] = relationship(
        "UserAchievement",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    prizes: Mapped[List["UserPrize"]] = relationship(
        "UserPrize",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
