from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class PrizeType(Base):
    """Типы призов"""
    
    __tablename__ = "prize_types"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    prize_value: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    user_prizes: Mapped[list["UserPrize"]] = relationship(
        back_populates="prize_type",
        cascade="all, delete-orphan"
    )


class UserPrize(Base):
    """Призы пользователей"""
    
    __tablename__ = "user_prizes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    prize_type_id: Mapped[int] = mapped_column(ForeignKey("prize_types.id"), nullable=False)
    
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="prizes")
    prize_type: Mapped["PrizeType"] = relationship(back_populates="user_prizes")
