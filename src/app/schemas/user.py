from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)


class UserResponse(UserBase):
    """Ответ с базовыми данными пользователя."""

    id: int
    energy: int = Field(..., ge=0)
    total_points: int = Field(..., ge=0)
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Ответ GET /users/ — список с общим количеством."""

    total: int = Field(..., ge=0, description="Всего пользователей в базе")
    items: list[UserResponse]