from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# PrizeType
# ---------------------------------------------------------------------------


class PrizeTypeBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Уникальный идентификатор типа приза (slug)",
        examples=["discount_10"],
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Человекочитаемое название приза",
        examples=["Скидка 10%"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=255,
        description="Описание приза для пользователя",
    )
    prize_value: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Значение приза (промокод, флаг и т.п.)",
        examples=["GENE10"],
    )


class PrizeTypeCreate(PrizeTypeBase):
    """Тело запроса для создания нового типа приза."""

    is_active: bool = Field(default=True, description="Доступен ли приз игрокам")


class PrizeTypeUpdate(BaseModel):
    """Тело запроса для частичного обновления типа приза.

    Все поля опциональны — передавайте только то, что нужно изменить.
    """

    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=255)
    prize_value: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class PrizeTypeResponse(PrizeTypeBase):
    """Ответ с данными типа приза."""

    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# UserPrize
# ---------------------------------------------------------------------------


class UserPrizeResponse(BaseModel):
    """Ответ с данными приза конкретного пользователя."""

    id: int = Field(..., description="ID записи UserPrize")
    prize_type_id: int = Field(..., description="ID типа приза")
    is_used: bool = Field(..., description="Был ли приз использован")
    awarded_at: datetime = Field(..., description="Когда приз был выдан")
    used_at: Optional[datetime] = Field(None, description="Когда приз был использован")

    model_config = {"from_attributes": True}


class UserPrizeDetailResponse(UserPrizeResponse):
    """Расширенный ответ: данные приза вложены напрямую."""

    prize_type: PrizeTypeResponse

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Query params
# ---------------------------------------------------------------------------


class PrizeListQueryParams(BaseModel):
    """Query-параметры для GET /prizes/."""

    skip: int = Field(default=0, ge=0, description="Смещение (пагинация)")
    limit: int = Field(default=100, ge=1, le=500, description="Максимум записей")
    active_only: bool = Field(default=False, description="Только активные призы")