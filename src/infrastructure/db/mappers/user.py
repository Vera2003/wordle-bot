"""Mappers for converting ORM models to domain/application objects."""

from datetime import datetime
from typing import cast
from uuid import UUID

from src.domain.user import User, TelegramId, Username, Energy
from src.infrastructure.db.models.user import UserModel


class UserMapper:
    """Mapper for User: ORM Model <-> Domain Entity."""
    
    @staticmethod
    def model_to_domain(model: UserModel) -> User:
        """Convert SQLAlchemy UserModel to domain User entity."""
        return User(
            id=cast(UUID, model.id),
            telegram_id=TelegramId(cast(int, model.telegram_id)),
            username=Username(cast(str | None, model.username)),
            full_name=cast(str | None, model.full_name),
            energy=Energy(cast(int, model.energy)),
            total_points=cast(int, model.total_points),
            created_at=cast(datetime | None, model.created_at),
            updated_at=cast(datetime | None, model.updated_at),
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
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
