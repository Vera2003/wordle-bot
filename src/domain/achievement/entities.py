"""Achievement domain entities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from .value_objects import AchievementRequirement, RewardType, RewardValue


class AchievementType:
    """
    Aggregate Root: An achievement definition (template).

    Defines what players need to do to unlock an achievement and what
    they get for doing it. Examples: "Win 10 games", "Reach level 5"
    """

    def __init__(
        self,
        id: UUID,
        name: str,
        title: str,
        description: str,
        requirement: AchievementRequirement,
        reward_type: RewardType,
        reward_value: RewardValue,
        created_at: Optional[datetime] = None,
    ):
        if not name or not isinstance(name, str):
            raise ValueError("Achievement name must be non-empty string")

        if not title or not isinstance(title, str):
            raise ValueError("Achievement title must be non-empty string")

        if not description or not isinstance(description, str):
            raise ValueError("Achievement description must be non-empty string")

        self._id = id
        self._name = name.lower()
        self._title = title
        self._description = description
        self._requirement = requirement
        self._reward_type = reward_type
        self._reward_value = reward_value
        self._created_at = created_at or datetime.now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        """Unique machine-readable name (lowercase)."""
        return self._name

    @property
    def title(self) -> str:
        """Human-readable title."""
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def requirement(self) -> AchievementRequirement:
        """What players need to do to unlock this."""
        return self._requirement

    @property
    def reward_type(self) -> RewardType:
        """What kind of reward."""
        return self._reward_type

    @property
    def reward_value(self) -> RewardValue:
        """The reward amount/description."""
        return self._reward_value

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def __repr__(self) -> str:
        return f"AchievementType(id={self._id}, name={self._name})"


class UserAchievement:
    """
    Entity: An instance of achievement unlocked by a user.

    Not an aggregate root - belongs to User aggregate.
    Records when a user unlocked a specific achievement.
    """

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        achievement_type_id: UUID,
        unlocked_at: Optional[datetime] = None,
    ):
        self._id = id
        self._user_id = user_id
        self._achievement_type_id = achievement_type_id
        self._unlocked_at = unlocked_at or datetime.now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def achievement_type_id(self) -> UUID:
        """ID of the AchievementType this user unlocked."""
        return self._achievement_type_id

    @property
    def unlocked_at(self) -> datetime:
        return self._unlocked_at

    def __repr__(self) -> str:
        return (
            f"UserAchievement(id={self._id}, user_id={self._user_id}, "
            f"achievement_id={self._achievement_type_id})"
        )
