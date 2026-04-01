"""Gene domain entity - aggregate root for genes/words."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from .errors import GeneNotActiveError
from .value_objects import GeneDifficulty, GeneName


class Gene:
    """
    Aggregate Root: A gene (word to guess).

    A Gene is a DNA-related word that players guess in the Wordle-bot game.
    Examples: MTHFR, APOE, BRCA1, etc.

    Properties:
    - Each gene has a name (the word players guess)
    - Difficulty level (easy/medium/hard) determines game difficulty
    - Description and hint for educational value
    - Active/inactive status (can turn off old genes)
    """

    def __init__(
        self,
        id: UUID,
        name: GeneName,
        description: str,
        hint: str,
        difficulty: GeneDifficulty,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
    ):
        if not description or not isinstance(description, str):
            raise ValueError("Description must be a non-empty string")

        if not hint or not isinstance(hint, str):
            raise ValueError("Hint must be a non-empty string")

        self._id = id
        self._name = name
        self._description = description
        self._hint = hint
        self._difficulty = difficulty
        self._is_active = is_active
        self._created_at = created_at or datetime.now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> GeneName:
        """The gene name (what players guess)."""
        return self._name

    @property
    def description(self) -> str:
        """Scientific description of the gene."""
        return self._description

    @property
    def hint(self) -> str:
        """First hint shown to player."""
        return self._hint

    @property
    def difficulty(self) -> GeneDifficulty:
        return self._difficulty

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def deactivate(self) -> None:
        """
        Deactivate this gene (cannot be used in new games).

        Used when rotating out old genes or correcting data.
        """
        self._is_active = False

    def activate(self) -> None:
        """Activate this gene (can be used in games again)."""
        self._is_active = True

    def update_details(
        self,
        *,
        description: str | None = None,
        hint: str | None = None,
        difficulty: GeneDifficulty | None = None,
    ) -> None:
        """Update editable gene attributes while preserving invariants."""
        if description is not None:
            if not description or not isinstance(description, str):
                raise ValueError("Description must be a non-empty string")
            self._description = description

        if hint is not None:
            if not hint or not isinstance(hint, str):
                raise ValueError("Hint must be a non-empty string")
            self._hint = hint

        if difficulty is not None:
            self._difficulty = difficulty

    def can_be_used(self) -> bool:
        """Check if this gene can be used for a new game."""
        if not self._is_active:
            raise GeneNotActiveError(f"Gene {self._name.value} is not active")
        return True

    def get_word(self) -> str:
        """Return the word (gene name) for guessing."""
        return self._name.value

    def get_word_length(self) -> int:
        """Return length of the word."""
        return self._name.length()

    def __repr__(self) -> str:
        return (
            f"Gene(id={self._id}, name={self._name.value}, "
            f"difficulty={self._difficulty.level}, is_active={self._is_active})"
        )
