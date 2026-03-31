"""Prize query handlers."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.prize.dto import PrizeOutput, UserPrizeOutput
from src.domain.prize import Prize, PrizeNotFoundError, PrizeRepository, UserPrize, UserPrizeRepository


def _to_prize_output(prize: Prize) -> PrizeOutput:
    return PrizeOutput(
        id=prize.id,
        name=prize.name,
        title=prize.title,
        description=prize.description,
        value=prize.value.value,
        is_active=prize.is_active,
        created_at=prize.created_at,
    )


def _to_user_prize_output(user_prize: UserPrize) -> UserPrizeOutput:
    return UserPrizeOutput(
        id=user_prize.id,
        user_id=user_prize.user_id,
        prize_id=user_prize.prize_id,
        is_used=user_prize.is_used,
        awarded_at=user_prize.awarded_at,
        used_at=user_prize.used_at,
    )


class GetPrizeByIdQuery(BaseModel):
    """Query to fetch a prize by ID."""

    model_config = ConfigDict(extra="forbid")

    prize_id: UUID


class GetPrizeByIdHandler:
    """Handler for GetPrizeById query."""

    def __init__(self, prize_repository: PrizeRepository):
        self.prize_repository = prize_repository

    async def __call__(self, query: GetPrizeByIdQuery) -> PrizeOutput:
        prize = await self.prize_repository.get_by_id(query.prize_id)
        if not prize:
            raise PrizeNotFoundError(f"Prize {query.prize_id} not found")
        return _to_prize_output(prize)


class GetActivePrizesQuery(BaseModel):
    """Query to fetch active prize definitions."""

    model_config = ConfigDict(extra="forbid")


class GetActivePrizesHandler:
    """Handler for GetActivePrizes query."""

    def __init__(self, prize_repository: PrizeRepository):
        self.prize_repository = prize_repository

    async def __call__(self, query: GetActivePrizesQuery) -> list[PrizeOutput]:
        del query
        prizes = await self.prize_repository.get_active_prizes()
        return [_to_prize_output(prize) for prize in prizes]


class GetUserPrizesQuery(BaseModel):
    """Query to fetch all prizes awarded to a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    used_only: bool = Field(default=False)


class GetUserPrizesHandler:
    """Handler for GetUserPrizes query."""

    def __init__(self, user_prize_repository: UserPrizeRepository):
        self.user_prize_repository = user_prize_repository

    async def __call__(self, query: GetUserPrizesQuery) -> list[UserPrizeOutput]:
        prizes = await self.user_prize_repository.get_user_prizes(
            user_id=query.user_id,
            used_only=query.used_only,
        )
        return [_to_user_prize_output(prize) for prize in prizes]


class GetUnusedUserPrizesQuery(BaseModel):
    """Query to fetch unused prizes for a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class GetUnusedUserPrizesHandler:
    """Handler for GetUnusedUserPrizes query."""

    def __init__(self, user_prize_repository: UserPrizeRepository):
        self.user_prize_repository = user_prize_repository

    async def __call__(self, query: GetUnusedUserPrizesQuery) -> list[UserPrizeOutput]:
        prizes = await self.user_prize_repository.get_unused_prizes(query.user_id)
        return [_to_user_prize_output(prize) for prize in prizes]
