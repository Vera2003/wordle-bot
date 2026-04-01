"""Achievement domain value objects."""

from __future__ import annotations

from enum import Enum


class RewardType(str, Enum):
    """Types of rewards for completing achievements."""

    POINTS = "points"
    HINTS = "hints"
    COINS = "coins"
    BADGE = "badge"
    MULTIPLIER = "multiplier"


class AchievementRequirement:
    """
    Value Object: The requirement for unlocking an achievement.

    Example: "win 10 games", "guess 100 words", "reach level 5"
    Stored as integer threshold (requirement value).
    """

    def __init__(self, value: int):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Achievement requirement must be positive integer")
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    def is_met(self, current_value: int) -> bool:
        """Check if current progress meets this requirement."""
        if current_value < 0:
            raise ValueError("Current progress cannot be negative")
        return current_value >= self._value

    def progress_percent(self, current_value: int) -> int:
        """Calculate progress as percentage (0-100)."""
        if current_value < 0:
            raise ValueError("Current progress cannot be negative")

        percent = int((current_value / self._value) * 100)
        return min(percent, 100)  # Cap at 100%

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AchievementRequirement):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"AchievementRequirement(value={self._value})"


class RewardValue:
    """
    Value Object: The actual reward value/quantity.

    Example: "100" points, "5" hints, "Premium badge"
    String because reward can be text (badge name) or numeric (points).
    """

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("Reward value must be non-empty string")

        if len(value) > 100:
            raise ValueError("Reward value cannot exceed 100 characters")

        self._value = value.strip()

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RewardValue):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"RewardValue(value={self._value!r})"
