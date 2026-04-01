"""User domain errors."""


class UserError(Exception):
    """Base user domain error."""

    pass


class UserNotFoundError(UserError):
    """User not found."""

    pass


class DuplicateTelegramIdError(UserError):
    """User with this Telegram ID already exists."""

    pass


class InvalidTelegramIdError(UserError):
    """Invalid Telegram ID."""

    pass


class InvalidUsernameError(UserError):
    """Invalid username."""

    pass
