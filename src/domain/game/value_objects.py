"""Game domain value objects - immutable values without identity."""

from typing import List, Literal

LetterState = Literal["correct", "present", "absent"]


class LetterStatus:
    """Value object: status of a letter in a guess."""

    def __init__(self, letter: str, status: LetterState):
        if not isinstance(letter, str) or len(letter) != 1:
            raise ValueError("Letter must be a single character")
        if status not in ("correct", "present", "absent"):
            raise ValueError(f"Invalid status: {status}")

        self._letter = letter.upper()
        self._status: LetterState = status

    @property
    def letter(self) -> str:
        return self._letter

    @property
    def status(self) -> LetterState:
        return self._status

    def is_correct(self) -> bool:
        return self._status == "correct"

    def is_present(self) -> bool:
        return self._status == "present"

    def is_absent(self) -> bool:
        return self._status == "absent"

    def __eq__(self, other) -> bool:
        if not isinstance(other, LetterStatus):
            return False
        return self._letter == other._letter and self._status == other._status

    def __hash__(self) -> int:
        return hash((self._letter, self._status))

    def __repr__(self) -> str:
        return f"LetterStatus(letter={self._letter}, status={self._status})"


class Word:
    """Value object: a word for guessing."""

    def __init__(self, value: str, max_length: int = 20):
        if not isinstance(value, str) or not value:
            raise ValueError("Word must be a non-empty string")
        if len(value) > max_length:
            raise ValueError(f"Word too long (max {max_length} chars)")

        self._value = value.upper()
        self._max_length = max_length

    @property
    def value(self) -> str:
        return self._value

    def length(self) -> int:
        return len(self._value)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Word):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"Word({self._value})"


class GuessResult:
    """Value object: result of checking a guess against a target word."""

    def __init__(self, letters: List[LetterStatus]):
        if not letters:
            raise ValueError("GuessResult must have at least one letter")
        self._letters = tuple(letters)  # Immutable

    @property
    def letters(self) -> tuple[LetterStatus, ...]:
        return self._letters

    def is_exact_match(self) -> bool:
        """All letters are correct."""
        return all(letter.is_correct() for letter in self._letters)

    def correct_count(self) -> int:
        """Count of correctly positioned letters."""
        return sum(1 for letter in self._letters if letter.is_correct())

    def present_count(self) -> int:
        """Count of letters in word but wrong position."""
        return sum(1 for letter in self._letters if letter.is_present())

    def __eq__(self, other) -> bool:
        if not isinstance(other, GuessResult):
            return False
        return self._letters == other._letters

    def __repr__(self) -> str:
        return f"GuessResult({[str(letter) for letter in self._letters]})"
