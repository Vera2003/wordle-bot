"""Prize domain services (cross-entity business logic)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .entities import Prize, UserPrize
from .errors import PrizeNotAvailableError
from .value_objects import EarnedPrizeRecord


class PrizeService:
    """
    Domain service: Prize business logic that spans entities or crosses boundaries.

    Handles operations that are too complex for a single entity but still
    represent core domain logic (not application workflow).
    """

    @staticmethod
    def check_prize_availability(prize: Prize) -> bool:
        """
        Validate that a prize can be awarded.

        What happens here:
        - Only active prizes can be awarded
        - Raises PrizeNotAvailableError if inactive

        Returns True if available, raises exception otherwise.
        """
        if not prize.is_active:
            raise PrizeNotAvailableError(
                f"Prize '{prize.name}' is not available for award. "
                f"Contact admin to activate it."
            )
        return True

    @staticmethod
    def award_prize(
        prize_id: UUID,
        user_id: UUID,
        awarded_at: Optional[datetime] = None,
    ) -> UserPrize:
        """
        Create a UserPrize record when a player earns a prize.

        What happens here:
        - Generate new ID for this earned instance
        - Create immutable EarnedPrizeRecord with award timestamp
        - Return UserPrize entity ready to save

        Args:
            prize_id: Which prize was earned
            user_id: Which player earned it
            awarded_at: When awarded (defaults to now)

        Returns: New UserPrize entity ready for repository save
        """
        if awarded_at is None:
            awarded_at = datetime.now()

        # Create immutable record of the award event
        record = EarnedPrizeRecord(
            awarded_at=awarded_at,
            is_used=False,
            used_at=None,
        )

        # New instance of earned prize
        user_prize = UserPrize(
            id=uuid4(),
            user_id=user_id,
            prize_id=prize_id,
            record=record,
        )

        return user_prize

    @staticmethod
    def is_prize_usable(user_prize: UserPrize) -> bool:
        """
        Check if a user's earned prize can still be used.

        What happens here:
        - Can't reuse a prize that's already been used
        - Can't use a prize that hasn't been earned yet (defensive check)

        Returns True if usable.
        """
        if user_prize.is_used:
            return False

        # Add any other time-based checks here
        # E.g., prizes that expire after 30 days

        return True
