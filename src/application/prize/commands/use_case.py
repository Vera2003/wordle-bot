"""Prize command handlers."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.application.prize.dto import PrizeOutput, UserPrizeOutput
from src.domain.prize import (
    EarnedPrizeRecord,
    Prize,
    PrizeNotAvailableError,
    PrizeNotFoundError,
    PrizeRepository,
    PrizeService,
    PrizeValue,
    UserPrize,
    UserPrizeRepository,
)


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


class CreatePrizeCommand(BaseModel):
    """Command to create a prize definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1, max_length=100)
    is_active: bool = Field(default=True)


class CreatePrizeHandler:
    """Handler for CreatePrize command."""

    def __init__(self, prize_repository: PrizeRepository):
        self.prize_repository = prize_repository

    async def __call__(self, command: CreatePrizeCommand) -> PrizeOutput:
        prize = Prize(
            id=uuid4(),
            name=command.name,
            title=command.title,
            description=command.description,
            value=PrizeValue(command.value),
            is_active=command.is_active,
        )
        await self.prize_repository.save(prize)
        return _to_prize_output(prize)


class AwardPrizeCommand(BaseModel):
    """Command to award a prize to a user."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    prize_id: UUID
    awarded_at: datetime | None = None


class AwardPrizeHandler:
    """Handler for AwardPrize command."""

    def __init__(
        self,
        prize_repository: PrizeRepository,
        user_prize_repository: UserPrizeRepository,
    ):
        self.prize_repository = prize_repository
        self.user_prize_repository = user_prize_repository

    async def __call__(self, command: AwardPrizeCommand) -> UserPrizeOutput:
        prize = await self.prize_repository.get_by_id(command.prize_id)
        if not prize:
            raise PrizeNotFoundError(f"Prize {command.prize_id} not found")

        PrizeService.check_prize_availability(prize)
        user_prize = PrizeService.award_prize(
            prize_id=command.prize_id,
            user_id=command.user_id,
            awarded_at=command.awarded_at,
        )
        await self.user_prize_repository.save(user_prize)
        return _to_user_prize_output(user_prize)


class MarkPrizeAsUsedCommand(BaseModel):
    """Command to mark an awarded prize as used."""

    model_config = ConfigDict(extra="forbid")

    user_prize_id: UUID
    used_at: datetime | None = None


class MarkPrizeAsUsedHandler:
    """Handler for MarkPrizeAsUsed command."""

    def __init__(self, user_prize_repository: UserPrizeRepository):
        self.user_prize_repository = user_prize_repository

    async def __call__(self, command: MarkPrizeAsUsedCommand) -> UserPrizeOutput:
        user_prize = await self.user_prize_repository.get_by_id(command.user_prize_id)
        if not user_prize:
            raise PrizeNotFoundError(f"User prize {command.user_prize_id} not found")

        user_prize.mark_as_used(command.used_at or datetime.now())
        await self.user_prize_repository.save(user_prize)
        return _to_user_prize_output(user_prize)
