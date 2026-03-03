from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class GeneBase(BaseModel):
    name: str = Field(
        ...,
        min_length=3,
        max_length=7,
        description="Название гена (5–7 символов, латиница и цифры)",
        examples=["MTHFR", "TCF7L2"],
    )
    description: str = Field(
        ...,
        min_length=20,
        description="Подробное описание функции гена",
    )
    hint: str = Field(
        ...,
        min_length=10,
        description="Короткая подсказка для игроков",
    )
    difficulty: str = Field(
        default="medium",
        pattern="^(easy|medium|hard)$",
        description="Сложность: easy | medium | hard",
    )

    @field_validator("name")
    @classmethod
    def name_uppercase(cls, v: str) -> str:
        return v.upper()


class GeneCreate(GeneBase):
    """Тело запроса POST /genes/ — создание нового гена."""

    is_active: bool = Field(default=True)


class GeneUpdate(BaseModel):
    """Тело запроса PUT /genes/{id} — частичное обновление.

    Все поля опциональны — передавайте только изменяемые.
    """

    name: Optional[str] = Field(None, min_length=5, max_length=7)
    description: Optional[str] = Field(None, min_length=20)
    hint: Optional[str] = Field(None, min_length=10)
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_uppercase(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v


class GeneResponse(GeneBase):
    """Ответ GET /genes/ и GET /genes/{id}."""

    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Query params
# ---------------------------------------------------------------------------


class GeneListQueryParams(BaseModel):
    """Query-параметры для GET /genes/."""

    skip: int = Field(default=0, ge=0, description="Смещение (пагинация)")
    limit: int = Field(default=100, ge=1, le=500, description="Максимум записей")
    active_only: bool = Field(default=False, description="Только активные гены")