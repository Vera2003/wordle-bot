"""Mappers for prize ORM models and domain entities."""

from src.domain.prize import EarnedPrizeRecord, Prize, PrizeValue, UserPrize
from src.infrastructure.db.models.prize import PrizeModel, UserPrizeModel


class PrizeMapper:
    """Mapper for Prize-related domain entities."""

    @staticmethod
    def model_to_domain(model: PrizeModel) -> Prize:
        return Prize(
            id=model.id,
            name=model.name,
            title=model.title,
            description=model.description,
            value=PrizeValue(model.prize_value),
            is_active=model.is_active,
            created_at=model.created_at,
        )

    @staticmethod
    def domain_to_model(prize: Prize) -> PrizeModel:
        return PrizeModel(
            id=prize.id,
            name=prize.name,
            title=prize.title,
            description=prize.description,
            prize_value=prize.value.value,
            is_active=prize.is_active,
            created_at=prize.created_at,
        )


class UserPrizeMapper:
    """Mapper for UserPrize domain entity."""

    @staticmethod
    def model_to_domain(model: UserPrizeModel) -> UserPrize:
        return UserPrize(
            id=model.id,
            user_id=model.user_id,
            prize_id=model.prize_id,
            record=EarnedPrizeRecord(
                awarded_at=model.awarded_at,
                is_used=model.is_used,
                used_at=model.used_at,
            ),
        )

    @staticmethod
    def domain_to_model(user_prize: UserPrize) -> UserPrizeModel:
        return UserPrizeModel(
            id=user_prize.id,
            user_id=user_prize.user_id,
            prize_id=user_prize.prize_id,
            is_used=user_prize.is_used,
            awarded_at=user_prize.awarded_at,
            used_at=user_prize.used_at,
        )
