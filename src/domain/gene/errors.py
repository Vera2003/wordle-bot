"""Gene domain errors."""


class GeneError(Exception):
    """Base exception for gene domain."""
    pass


class GeneNotFoundError(GeneError):
    """Gene not found."""
    pass


class InvalidGeneNameError(GeneError):
    """Gene name is invalid."""
    pass


class GeneDifficultyError(GeneError):
    """Gene difficulty level is invalid."""
    pass


class GeneNotActiveError(GeneError):
    """Gene is not active and cannot be used."""
    pass
