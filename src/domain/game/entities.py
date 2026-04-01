"""Game domain entity - the main aggregate root."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID

from .errors import GameAlreadyFinishedError, InvalidGuessError, NoAttemptsLeftError
from .value_objects import GuessResult, LetterStatus, Word


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GameAttempt:
    """Entity: a single attempt to guess the word."""

    def __init__(
        self,
        attempt_number: int,
        guess: Word,
        result: GuessResult,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
    ):
        if attempt_number < 1:
            raise ValueError("Attempt number must be >= 1")

        self.id = id or uuid.uuid4()
        self.attempt_number = attempt_number
        self.guess = guess
        self.result = result
        self.created_at = created_at or _utc_now()

    def is_correct(self) -> bool:
        """Was the guess correct?"""
        return self.result.is_exact_match()

    def __repr__(self) -> str:
        return (
            f"GameAttempt(id={self.id}, attempt={self.attempt_number}, "
            f"guess={self.guess.value}, is_correct={self.is_correct()})"
        )


class GameSession:
    """
    Aggregate Root: a game session.

    Contains all game logic and rules. This is the main entity in the Game context.
    """

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        target_word: Word,
        max_attempts: int = 6,
        created_at: Optional[datetime] = None,
    ):
        if max_attempts < 1:
            raise ValueError("Max attempts must be >= 1")

        self.id = id
        self.user_id = user_id
        self._target_word = target_word
        self._max_attempts = max_attempts
        self._attempts: List[GameAttempt] = []
        self._is_won = False
        self._is_finished = False
        self.created_at = created_at or _utc_now()
        self.finished_at: Optional[datetime] = None
        self.points_earned = 0
        self.hint_used = False

    @property
    def target_word(self) -> Word:
        """The word to guess (only accessible internally in domain)."""
        return self._target_word

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def attempts(self) -> List[GameAttempt]:
        """All attempts made in this game."""
        return list(self._attempts)  # Return copy to prevent external modification

    @property
    def attempt_count(self) -> int:
        """Number of attempts made so far."""
        return len(self._attempts)

    @property
    def attempts_left(self) -> int:
        """Attempts remaining."""
        return max(0, self._max_attempts - self.attempt_count)

    @property
    def is_won(self) -> bool:
        return self._is_won

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    @property
    def last_attempt(self) -> Optional[GameAttempt]:
        """Get the most recent attempt."""
        return self._attempts[-1] if self._attempts else None

    def make_attempt(self, guess: Word) -> GameAttempt:
        """
        Make an attempt to guess the word.

        Returns:
            GameAttempt with the result

        Raises:
            GameAlreadyFinishedError: if game is already finished
            NoAttemptsLeftError: if no attempts left
            InvalidGuessError: if guess is invalid
        """
        if self._is_finished:
            raise GameAlreadyFinishedError("Cannot make attempt on finished game")

        if self.attempts_left == 0:
            raise NoAttemptsLeftError("No attempts left")

        # Check guess validity (must be same length as target)
        if guess.length() != self._target_word.length():
            raise InvalidGuessError(
                f"Guess must be {self._target_word.length()} letters long, "
                f"got {guess.length()}"
            )

        # Check the guess and create GuessResult
        result = self._check_guess(guess)

        # Create attempt
        attempt = GameAttempt(
            attempt_number=self.attempt_count + 1,
            guess=guess,
            result=result,
        )
        self._attempts.append(attempt)

        # Update game state
        if result.is_exact_match():
            self._is_won = True
            self._is_finished = True
            self.finished_at = _utc_now()
            # Calculate points: more points for fewer attempts
            self.points_earned = max(
                0, (self._max_attempts - self.attempt_count + 1) * 10
            )
        elif self.attempts_left == 0:
            self._is_finished = True
            self.finished_at = _utc_now()
            self.points_earned = 0

        return attempt

    def _check_guess(self, guess: Word) -> GuessResult:
        """
        Check if guess matches target word.

        Returns GuessResult with letter statuses.
        This is the core game logic.
        """
        target = self._target_word.value
        guess_str = guess.value

        letters: List[LetterStatus] = []
        target_chars: List[str | None] = list(target)

        # First pass: mark correct positions
        status_map: List[Literal["unknown", "correct", "present", "absent"]] = [
            "unknown"
        ] * len(guess_str)
        for i, char in enumerate(guess_str):
            if char == target[i]:
                status_map[i] = "correct"
                target_chars[i] = None  # Mark as used

        # Second pass: check for present letters
        for i, char in enumerate(guess_str):
            if status_map[i] == "unknown":
                if char in target_chars:
                    status_map[i] = "present"
                    target_chars[target_chars.index(char)] = None
                else:
                    status_map[i] = "absent"

        # Create LetterStatus objects
        for i, char in enumerate(guess_str):
            status = status_map[i]
            if status == "unknown":
                status = "absent"
            letters.append(LetterStatus(char, status))

        return GuessResult(letters)

    def use_hint(self) -> bool:
        """Mark that hint was used."""
        if self._is_finished:
            raise GameAlreadyFinishedError("Cannot use hint on finished game")
        if self.hint_used:
            return False
        self.hint_used = True
        return True

    def surrender(self, finished_at: Optional[datetime] = None) -> None:
        """Finish the game as a loss without awarding points."""
        if self._is_finished:
            return
        self._is_finished = True
        self._is_won = False
        self.finished_at = finished_at or _utc_now()
        self.points_earned = 0

    def is_over(self) -> bool:
        """Game is over (won or lost)."""
        return self._is_finished

    def __repr__(self) -> str:
        return (
            f"GameSession(id={self.id}, user={self.user_id}, "
            f"attempts={self.attempt_count}/{self._max_attempts}, "
            f"is_won={self._is_won})"
        )
