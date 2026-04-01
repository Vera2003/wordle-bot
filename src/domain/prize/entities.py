"""Prize domain entities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from .errors import PrizeNotAvailableError
from .value_objects import EarnedPrizeRecord, PrizeValue


class Prize:
    """
    Aggregate Root: A prize definition (template).

    A Prize is a reward that can be earned/purchased by players.
    Examples: "Discord invite", "Premium badge", "Hint tokens"
    """

    def __init__(
        self,
        id: UUID,
        name: str,
        title: str,
        description: str,
        value: PrizeValue,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
    ):
        if not name or not isinstance(name, str):
            raise ValueError("Prize name must be non-empty string")

        if not title or not isinstance(title, str):
            raise ValueError("Prize title must be non-empty string")

        if not description or not isinstance(description, str):
            raise ValueError("Prize description must be non-empty string")

        self._id = id
        self._name = name.lower()
        self._title = title
        self._description = description
        self._value = value
        self._is_active = is_active
        self._created_at = created_at or datetime.now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        """Unique machine-readable name."""
        return self._name

    @property
    def title(self) -> str:
        """Human-readable title."""
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def value(self) -> PrizeValue:
        """What the prize actually is."""
        return self._value

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def can_be_awarded(self) -> bool:
        """Check if this prize can be awarded to users."""
        if not self._is_active:
            raise PrizeNotAvailableError(f"Prize {self._name} is not active")
        return True

    def deactivate(self) -> None:
        """Stop awarding this prize."""
        self._is_active = False

    def activate(self) -> None:
        """Allow this prize to be awarded again."""
        self._is_active = True

    def update_details(
        self,
        *,
        description: str | None = None,
        value: PrizeValue | None = None,
    ) -> None:
        """Update editable prize attributes."""
        if description is not None:
            if not description or not isinstance(description, str):
                raise ValueError("Prize description must be non-empty string")
            self._description = description

        if value is not None:
            self._value = value

    def __repr__(self) -> str:
        return f"Prize(id={self._id}, name={self._name}, is_active={self._is_active})"


class UserPrize:
    """
    Entity: An instance of a prize earned by a user.

    Not an aggregate root - it belongs to User aggregate.
    Tracks when prize was earned and whether it's been used/claimed.
    """

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        prize_id: UUID,
        record: EarnedPrizeRecord,
    ):
        self._id = id
        self._user_id = user_id
        self._prize_id = prize_id
        self._record = record

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def prize_id(self) -> UUID:
        """ID of the Prize definition."""
        return self._prize_id

    @property
    def awarded_at(self) -> datetime:
        return self._record.awarded_at

    @property
    def is_used(self) -> bool:
        return self._record.is_used

    @property
    def used_at(self) -> Optional[datetime]:
        return self._record.used_at

    def mark_as_used(self, used_at: datetime) -> None:
        """Mark prize as claimed/used by user."""
        if self._record.is_used:
            raise ValueError("Prize already marked as used")

        # Create new immutable record
        self._record = EarnedPrizeRecord(
            awarded_at=self._record.awarded_at,
            is_used=True,
            used_at=used_at,
        )

    def __repr__(self) -> str:
        status = "used" if self.is_used else "unused"
        return (
            f"UserPrize(id={self._id}, user_id={self._user_id}, "
            f"prize_id={self._prize_id}, status={status})"
        )
