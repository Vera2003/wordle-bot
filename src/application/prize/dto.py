"""Prize application DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from ..common.dto import BaseDTO


class PrizeOutput(BaseDTO):
    """Read DTO for a prize definition."""

    id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(...)
    value: str = Field(..., min_length=1, max_length=100)
    is_active: bool = Field(...)
    created_at: datetime = Field(...)


class UserPrizeOutput(BaseDTO):
    """Read DTO for a prize awarded to a user."""

    id: UUID = Field(...)
    user_id: UUID = Field(...)
    prize_id: UUID = Field(...)
    is_used: bool = Field(...)
    awarded_at: datetime = Field(...)
    used_at: datetime | None = Field(None)
