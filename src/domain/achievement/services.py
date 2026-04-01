"""Achievement domain services (cross-entity business logic)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .entities import AchievementType, UserAchievement
from .errors import AchievementAlreadyUnlockedError, AchievementRequirementNotMetError


class AchievementService:
    """
    Domain service: Achievement business logic that spans entities or crosses boundaries.

    Main responsibilities:
    - Validate requirement satisfaction
    - Check if user can unlock achievement
    - Track progress toward requirements
    """

    @staticmethod
    def can_unlock_achievement(
        achievement_type: AchievementType,
        current_progress: int,
        already_unlocked: bool = False,
    ) -> bool:
        """
        Check if user should unlock this achievement.

        What happens here:
        - Verify user hasn't already unlocked it (no double-unlock)
        - Verify current progress meets requirement
        - Raises exceptions if conditions not met

        Args:
            achievement_type: Definition of achievement
            current_progress: User's current progress value
            already_unlocked: Whether user already has this achievement

        Returns: True if can unlock, raises exception otherwise
        """
        if already_unlocked:
            raise AchievementAlreadyUnlockedError(
                f"User already unlocked '{achievement_type.name}'"
            )

        if not achievement_type.requirement.is_met(current_progress):
            raise AchievementRequirementNotMetError(
                f"Requirement not met for '{achievement_type.name}'. "
                f"Current: {current_progress}, Required: {achievement_type.requirement.value}"
            )

        return True

    @staticmethod
    def calculate_progress(
        achievement_type: AchievementType,
        current_value: int,
    ) -> int:
        """
        Calculate percentage progress toward achievement.

        What happens here:
        - Use requirement to calculate 0-100% progress
        - Cap at 100% if already exceeded requirement

        Useful for: progress bars, notifications, analytics

        Args:
            achievement_type: Achievement definition
            current_value: Current progress value

        Returns: Progress percentage (0-100)
        """
        return achievement_type.requirement.progress_percent(current_value)

    @staticmethod
    def unlock_achievement(
        achievement_type_id: UUID,
        user_id: UUID,
        unlocked_at: Optional[datetime] = None,
    ) -> UserAchievement:
        """
        Create a UserAchievement record when player unlocks an achievement.

        What happens here:
        - Generate new ID for this unlock record
        - Capture unlock timestamp
        - Return UserAchievement entity ready to save

        Args:
            achievement_type_id: Which achievement was unlocked
            user_id: Which player unlocked it
            unlocked_at: When unlocked (defaults to now)

        Returns: New UserAchievement entity ready for repository save
        """
        if unlocked_at is None:
            unlocked_at = datetime.now()

        user_achievement = UserAchievement(
            id=uuid4(),
            user_id=user_id,
            achievement_type_id=achievement_type_id,
            unlocked_at=unlocked_at,
        )

        return user_achievement
