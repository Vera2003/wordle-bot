"""Prize domain value objects."""

from datetime import datetime


class PrizeValue:
    """
    Value object: The reward value of a prize.

    Examples: "Discord server invite", "1 month free access", "Premium badge"
    """

    def __init__(self, value: str):
        if not value or not isinstance(value, str) or len(value) > 100:
            raise ValueError("Prize value must be a non-empty string (max 100 chars)")

        self._value = value.strip()

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other) -> bool:
        if not isinstance(other, PrizeValue):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"PrizeValue({self._value!r})"


class EarnedPrizeRecord:
    """
    Value object: Record of a prize earned by a user.

    Immutable snapshot of when prize was awarded.
    """

    def __init__(
        self,
        awarded_at: datetime,
        is_used: bool = False,
        used_at: datetime | None = None,
    ):
        if is_used and not used_at:
            raise ValueError("If prize is used, used_at must be provided")

        if not is_used and used_at:
            raise ValueError("If prize is not used, used_at must be None")

        self._awarded_at = awarded_at
        self._is_used = is_used
        self._used_at = used_at

    @property
    def awarded_at(self) -> datetime:
        return self._awarded_at

    @property
    def is_used(self) -> bool:
        return self._is_used

    @property
    def used_at(self) -> datetime | None:
        return self._used_at

    def __repr__(self) -> str:
        status = "used" if self._is_used else "unused"
        return f"EarnedPrizeRecord(awarded_at={self._awarded_at}, status={status})"
