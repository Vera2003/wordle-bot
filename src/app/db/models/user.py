from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, List

from ..base import Base

if TYPE_CHECKING:
    from .game import GameSession
    from .achievements import UserAchievement
    from .prize import UserPrize


class User(Base):
    """Модель пользователя"""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    energy: Mapped[int] = mapped_column(Integer, default=5)
    last_energy_reset: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Связи - используем строковые ссылки
    game_sessions: Mapped[List["GameSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    achievements: Mapped[List["UserAchievement"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    prizes: Mapped[List["UserPrize"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
