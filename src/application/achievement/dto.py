"""Achievement application DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from ..common.dto import BaseDTO


class AchievementTypeOutput(BaseDTO):
    """Read DTO for an achievement definition."""

    id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(...)
    requirement_value: int = Field(..., gt=0)
    reward_type: str = Field(...)
    reward_value: str = Field(..., min_length=1, max_length=100)
    created_at: datetime = Field(...)


class UserAchievementOutput(BaseDTO):
    """Read DTO for an achievement unlocked by a user."""

    id: UUID = Field(...)
    user_id: UUID = Field(...)
    achievement_type_id: UUID = Field(...)
    unlocked_at: datetime = Field(...)


class AchievementProgressOutput(BaseDTO):
    """Read DTO for user progress toward an achievement."""

    achievement: AchievementTypeOutput = Field(...)
    current_progress: int = Field(..., ge=0)
    progress_percent: int = Field(..., ge=0, le=100)
    is_unlocked: bool = Field(...)
