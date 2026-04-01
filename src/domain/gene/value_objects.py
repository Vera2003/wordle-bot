"""Gene domain value objects - immutable values without identity."""


class GeneName:
    """
    Value object: Gene name (like MTHFR, APOE).

    Rules:
    - Must be 1-10 characters
    - Must be uppercase
    - Must be unique (checked at repository level)
    """

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("Gene name must be a non-empty string")

        value = value.upper().strip()

        if len(value) < 1 or len(value) > 10:
            raise ValueError("Gene name must be 1-10 characters")

        if not value.isalpha():
            raise ValueError("Gene name must only contain letters")

        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def length(self) -> int:
        """Length of the gene name."""
        return len(self._value)

    def __eq__(self, other) -> bool:
        if not isinstance(other, GeneName):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"GeneName({self._value})"


class GeneDifficulty:
    """
    Value object: Gene difficulty level.

    Rules:
    - Must be one of: easy, medium, hard
    - Used to determine word length and hints
    """

    LEVELS = ("easy", "medium", "hard")

    def __init__(self, level: str):
        if level not in self.LEVELS:
            raise ValueError(f"Difficulty must be one of {self.LEVELS}, got {level}")

        self._level = level

    @property
    def level(self) -> str:
        return self._level

    def is_easy(self) -> bool:
        return self._level == "easy"

    def is_medium(self) -> bool:
        return self._level == "medium"

    def is_hard(self) -> bool:
        return self._level == "hard"

    def __eq__(self, other) -> bool:
        if not isinstance(other, GeneDifficulty):
            return False
        return self._level == other._level

    def __hash__(self) -> int:
        return hash(self._level)

    def __repr__(self) -> str:
        return f"GeneDifficulty({self._level})"
