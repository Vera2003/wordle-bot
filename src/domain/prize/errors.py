"""Prize domain errors."""


class PrizeError(Exception):
    """Base exception for prize domain."""
    pass


class PrizeNotFoundError(PrizeError):
    """Prize not found."""
    pass


class PrizeNotAvailableError(PrizeError):
    """Prize is not available (inactive or out of stock)."""
    pass


class InsufficientPointsError(PrizeError):
    """User doesn't have enough points to redeem prize."""
    pass
