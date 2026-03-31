"""Gene application DTOs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from ..common.dto import BaseDTO


class GeneOutput(BaseDTO):
    """Read DTO for a gene."""

    id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=10)
    description: str = Field(...)
    hint: str = Field(...)
    difficulty: Literal["easy", "medium", "hard"] = Field(...)
    is_active: bool = Field(...)
    created_at: datetime = Field(...)


class GeneSummaryOutput(BaseDTO):
    """Compact DTO for gene listings."""

    id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=10)
    difficulty: Literal["easy", "medium", "hard"] = Field(...)
    is_active: bool = Field(...)
