"""User domain value objects."""

from typing import Optional


class TelegramId:
    """Value object: Telegram user ID."""

    def __init__(self, value: int):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Telegram ID must be a positive integer")
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    def __eq__(self, other) -> bool:
        if not isinstance(other, TelegramId):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"TelegramId({self._value})"


class Username:
    """Value object: Username."""

    def __init__(self, value: Optional[str]):
        if value is not None:
            if not isinstance(value, str) or not (1 <= len(value) <= 32):
                raise ValueError("Username must be 1-32 characters")
        self._value = value

    @property
    def value(self) -> Optional[str]:
        return self._value

    def __eq__(self, other) -> bool:
        if not isinstance(other, Username):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value) if self._value else 0

    def __repr__(self) -> str:
        return f"Username({self._value})"


class Energy:
    """Value object: User energy (for playing games)."""

    def __init__(self, value: int, max_energy: int = 5):
        if not isinstance(value, int) or value < 0:
            raise ValueError("Energy must be non-negative")
        if value > max_energy:
            raise ValueError(f"Energy cannot exceed max ({max_energy})")
        self._value = value
        self._max = max_energy

    @property
    def value(self) -> int:
        return self._value

    @property
    def max(self) -> int:
        return self._max

    def is_depleted(self) -> bool:
        return self._value == 0

    def is_full(self) -> bool:
        return self._value == self._max

    def use_energy(self) -> "Energy":
        """Use one energy point."""
        if self.is_depleted():
            raise ValueError("No energy left")
        return Energy(self._value - 1, self._max)

    def restore(self) -> "Energy":
        """Restore to full energy."""
        return Energy(self._max, self._max)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Energy):
            return False
        return self._value == other._value and self._max == other._max

    def __repr__(self) -> str:
        return f"Energy({self._value}/{self._max})"
