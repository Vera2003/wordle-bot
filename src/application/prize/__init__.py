"""Prize application layer module."""

from .commands import (
    AwardPrizeCommand,
    AwardPrizeHandler,
    CreatePrizeCommand,
    CreatePrizeHandler,
    MarkPrizeAsUsedCommand,
    MarkPrizeAsUsedHandler,
)
from .dto import PrizeOutput, UserPrizeOutput
from .queries import (
    GetActivePrizesHandler,
    GetActivePrizesQuery,
    GetPrizeByIdHandler,
    GetPrizeByIdQuery,
    GetUnusedUserPrizesHandler,
    GetUnusedUserPrizesQuery,
    GetUserPrizesHandler,
    GetUserPrizesQuery,
)

__all__ = [
    "PrizeOutput",
    "UserPrizeOutput",
    "CreatePrizeCommand",
    "CreatePrizeHandler",
    "AwardPrizeCommand",
    "AwardPrizeHandler",
    "MarkPrizeAsUsedCommand",
    "MarkPrizeAsUsedHandler",
    "GetPrizeByIdHandler",
    "GetPrizeByIdQuery",
    "GetActivePrizesHandler",
    "GetActivePrizesQuery",
    "GetUserPrizesHandler",
    "GetUserPrizesQuery",
    "GetUnusedUserPrizesHandler",
    "GetUnusedUserPrizesQuery",
]
