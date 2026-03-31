"""Integration tests for Prize repositories."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.prize import EarnedPrizeRecord, Prize, PrizeValue, UserPrize
from src.infrastructure.db.models.user import UserModel
from src.infrastructure.db.repositories.prize import PrizeRepositoryImpl, UserPrizeRepositoryImpl


@pytest.mark.asyncio
async def test_prize_repository_save_and_get_active_prizes(db):
    repo = PrizeRepositoryImpl(db)

    active_prize = Prize(
        id=uuid4(),
        name="discount_10",
        title="10% Discount",
        description="Discount for next order.",
        value=PrizeValue("GENE10"),
        is_active=True,
    )
    inactive_prize = Prize(
        id=uuid4(),
        name="hidden_badge",
        title="Hidden Badge",
        description="Secret achievement badge.",
        value=PrizeValue("hidden-badge"),
        is_active=False,
    )

    await repo.save(active_prize)
    await repo.save(inactive_prize)

    loaded_by_name = await repo.get_by_name("discount_10")
    active_prizes = await repo.get_active_prizes()

    assert loaded_by_name is not None
    assert loaded_by_name.id == active_prize.id
    assert [item.id for item in active_prizes] == [active_prize.id]


@pytest.mark.asyncio
async def test_user_prize_repository_save_update_and_filter_unused(db):
    prize_repo = PrizeRepositoryImpl(db)
    user_prize_repo = UserPrizeRepositoryImpl(db)

    user = UserModel(id=uuid4(), telegram_id=123456789, username="alice", full_name="Alice")
    db.add(user)

    prize = Prize(
        id=uuid4(),
        name="premium_badge",
        title="Premium Badge",
        description="Permanent profile badge.",
        value=PrizeValue("premium"),
    )
    await prize_repo.save(prize)

    user_prize = UserPrize(
        id=uuid4(),
        user_id=user.id,
        prize_id=prize.id,
        record=EarnedPrizeRecord(awarded_at=datetime(2026, 1, 1, 12, 0, 0)),
    )
    await user_prize_repo.save(user_prize)

    unused = await user_prize_repo.get_unused_prizes(user.id)
    assert [item.id for item in unused] == [user_prize.id]

    user_prize.mark_as_used(datetime(2026, 1, 2, 12, 0, 0))
    await user_prize_repo.save(user_prize)

    loaded = await user_prize_repo.get_by_id(user_prize.id)
    unused_after = await user_prize_repo.get_unused_prizes(user.id)
    used_only = await user_prize_repo.get_user_prizes(user.id, used_only=True)

    assert loaded is not None
    assert loaded.is_used is True
    assert loaded.used_at == datetime(2026, 1, 2, 12, 0, 0)
    assert unused_after == []
    assert [item.id for item in used_only] == [user_prize.id]
