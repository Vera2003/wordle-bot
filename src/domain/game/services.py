"""Game domain services - pure business logic."""

from typing import Optional

from .entities import GameSession
from .value_objects import Word


class GameDomainService:
    """
    Domain service: business logic that involves Game logic.
    Pure domain logic - no infrastructure, no async.
    """

    @staticmethod
    def calculate_points(attempts_used: int, max_attempts: int, is_won: bool) -> int:
        """
        Calculate points for completing a game.

        More points for:
        - Winning (0 points for losing)
        - Using fewer attempts
        """
        if not is_won:
            return 0

        remaining = max_attempts - attempts_used
        return max(10, (remaining + 1) * 10)

    @staticmethod
    def check_game_over_conditions(
        game: GameSession,
    ) -> tuple[bool, bool]:
        """
        Check if game should be marked as finished.

        Returns:
            (is_finished, is_won)
        """
        last_attempt = game.last_attempt

        if not last_attempt:
            return False, False

        # Win condition
        if last_attempt.is_correct():
            return True, True

        # Lost condition (no attempts left)
        if game.attempts_left == 0:
            return True, False

        return False, False

    @staticmethod
    def get_hint_letter(word: Word, game: GameSession) -> Optional[str]:
        """
        Get a hint letter for the player.

        Returns a random correct letter that hasn't appeared in attempts yet.
        """
        target_word = word.value
        attempted_letters = set()

        for attempt in game.attempts:
            for letter_status in attempt.result.letters:
                attempted_letters.add(letter_status.letter)

        # Find letters in target that haven't been guessed correctly yet
        hints = [c for c in target_word if c not in attempted_letters]

        if not hints:
            # If all letters have been guessed, return None
            return None

        # Return any available hint letter
        return hints[0]
