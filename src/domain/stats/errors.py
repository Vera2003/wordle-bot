"""Stats domain errors."""


class StatsError(Exception):
    """Base stats domain error."""
    pass


class UserNotFoundError(StatsError):
    """User not found for stats query."""
    pass


class InvalidWinRateError(StatsError):
    """Invalid win rate calculation."""
    pass
