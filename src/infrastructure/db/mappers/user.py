"""Mappers for converting ORM models to domain/application objects."""

from src.domain.user import Energy, TelegramId, User, Username
from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.models.user import UserModel


class UserMapper:
    """Mapper for User: ORM Model <-> Domain Entity."""

    @staticmethod
    def model_to_domain(model: UserModel) -> User:
        """Convert SQLAlchemy UserModel to domain User entity."""
        settings = get_settings()
        return User(
            id=model.id,
            telegram_id=TelegramId(model.telegram_id),
            username=Username(model.username),
            full_name=model.full_name,
            energy=Energy(model.energy, settings.daily_energy),
            total_points=model.total_points,
            last_energy_reset=model.last_energy_reset,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def domain_to_model(user: User) -> UserModel:
        """Convert domain User entity to SQLAlchemy UserModel."""
        return UserModel(
            id=user.id,
            telegram_id=user.telegram_id.value,
            username=user.username.value if user.username else None,
            full_name=user.full_name,
            energy=user.energy.value,
            total_points=user.total_points,
            last_energy_reset=user.last_energy_reset,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
