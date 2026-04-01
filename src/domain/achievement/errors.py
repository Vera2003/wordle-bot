"""Achievement domain errors."""


class AchievementError(Exception):
    """Base exception for achievement domain."""

    pass


class AchievementTypeNotFoundError(AchievementError):
    """Achievement type definition not found in database."""

    pass


class AchievementAlreadyUnlockedError(AchievementError):
    """User already has this achievement."""

    pass


class InvalidAchievementRequirementError(AchievementError):
    """Requirement value is invalid for this achievement type."""

    pass


class AchievementRequirementNotMetError(AchievementError):
    """User doesn't meet the requirements to unlock achievement."""

    pass
