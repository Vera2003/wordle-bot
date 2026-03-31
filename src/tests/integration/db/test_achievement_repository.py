"""Integration tests for Achievement repositories."""

import pytest
from uuid import uuid4

from src.domain.achievement import (
    AchievementRequirement,
    AchievementType,
    RewardType,
    RewardValue,
    UserAchievement,
)
from src.infrastructure.db.models.user import UserModel
from src.infrastructure.db.repositories.achievement import (
    AchievementTypeRepositoryImpl,
    UserAchievementRepositoryImpl,
)


@pytest.mark.asyncio
async def test_achievement_type_repository_save_and_get_by_name(db):
    repo = AchievementTypeRepositoryImpl(db)

    achievement = AchievementType(
        id=uuid4(),
        name="win_10_games",
        title="Ten Wins",
        description="Win ten finished games.",
        requirement=AchievementRequirement(10),
        reward_type=RewardType.POINTS,
        reward_value=RewardValue("100"),
    )

    await repo.save(achievement)

    loaded = await repo.get_by_name("win_10_games")
    all_items = await repo.get_all()

    assert loaded is not None
    assert loaded.id == achievement.id
    assert loaded.requirement.value == 10
    assert [item.id for item in all_items] == [achievement.id]


@pytest.mark.asyncio
async def test_user_achievement_repository_save_and_lookup(db):
    achievement_repo = AchievementTypeRepositoryImpl(db)
    user_achievement_repo = UserAchievementRepositoryImpl(db)

    user = UserModel(id=uuid4(), telegram_id=987654321, username="bob", full_name="Bob")
    db.add(user)

    achievement = AchievementType(
        id=uuid4(),
        name="first_win",
        title="First Win",
        description="Win your first game.",
        requirement=AchievementRequirement(1),
        reward_type=RewardType.BADGE,
        reward_value=RewardValue("winner"),
    )
    await achievement_repo.save(achievement)

    user_achievement = UserAchievement(
        id=uuid4(),
        user_id=user.id,
        achievement_type_id=achievement.id,
    )
    await user_achievement_repo.save(user_achievement)

    loaded = await user_achievement_repo.get_by_user_and_achievement(user.id, achievement.id)
    user_items = await user_achievement_repo.get_user_achievements(user.id)

    assert loaded is not None
    assert loaded.id == user_achievement.id
    assert [item.id for item in user_items] == [user_achievement.id]
