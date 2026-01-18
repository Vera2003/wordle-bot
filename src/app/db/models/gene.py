from datetime import datetime
from sqlalchemy import Integer, String, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from ..base import Base


class Gene(Base):
    """Модель гена"""
    
    __tablename__ = "genes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")  # easy, medium, hard
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Связи
    game_sessions: Mapped[List["GameSession"]] = relationship(
        "GameSession",
        back_populates="gene"
    )
    
    def __repr__(self) -> str:
        return f"<Gene(id={self.id}, name={self.name}, difficulty={self.difficulty})>"
    
    @property
    def length(self) -> int:
        """Длина названия гена"""
        return len(self.name)
