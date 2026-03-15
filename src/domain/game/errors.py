"""Game domain errors."""


class GameError(Exception):
    """Base game domain error."""
    pass


class GameNotFoundError(GameError):
    """Game session not found."""
    pass


class InvalidGuessError(GameError):
    """Guess is invalid (too long, contains invalid chars, etc)."""
    pass


class GameAlreadyFinishedError(GameError):
    """Cannot make attempt on finished game."""
    pass


class NoAttemptsLeftError(GameError):
    """Game is over - no attempts left."""
    pass
