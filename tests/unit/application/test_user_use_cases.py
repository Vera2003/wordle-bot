"""Unit tests for User application use cases."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.user.commands import (
    AddPointsCommand,
    AddPointsHandler,
    GetOrCreateUserCommand,
    GetOrCreateUserHandler,
    RestoreEnergyCommand,
    RestoreEnergyHandler,
    UseEnergyCommand,
    UseEnergyHandler,
)
from src.application.user.queries import GetUserProfileHandler, GetUserProfileQuery
from src.domain.user import Energy, TelegramId, User, Username, UserNotFoundError
from src.infrastructure.config.settings import get_settings


class TestGetOrCreateUserHandler:
    """Tests for GetOrCreateUser use case."""

    @pytest.mark.asyncio
    async def test_get_existing_user(self):
        """Test getting existing user."""
        user_id = uuid4()
        existing_user = User(
            id=user_id,
            telegram_id=TelegramId(123456789),
            username=Username("john"),
            full_name="John Doe",
        )

        repository = AsyncMock()
        repository.get_by_telegram_id.return_value = existing_user

        handler = GetOrCreateUserHandler(
            repository, daily_energy=get_settings().daily_energy
        )
        command = GetOrCreateUserCommand(
            telegram_id=123456789, username="john", full_name="John Doe"
        )

        result = await handler(command)

        assert result.user_id == user_id
        assert result.telegram_id == 123456789
        assert result.is_new is False
        repository.get_by_telegram_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_new_user(self):
        """Test creating new user."""
        settings = get_settings()
        repository = AsyncMock()
        repository.get_by_telegram_id.return_value = None
        repository.save = AsyncMock()

        handler = GetOrCreateUserHandler(
            repository, daily_energy=get_settings().daily_energy
        )
        command = GetOrCreateUserCommand(
            telegram_id=123456789, username="jane", full_name="Jane Doe"
        )

        result = await handler(command)

        assert result.telegram_id == 123456789
        assert result.username == "jane"
        assert result.full_name == "Jane Doe"
        assert result.is_new is True
        assert result.energy == settings.daily_energy
        repository.save.assert_called_once()


class TestAddPointsHandler:
    """Tests for AddPoints use case."""

    @pytest.mark.asyncio
    async def test_add_points_success(self):
        """Test adding points successfully."""
        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=TelegramId(123456789),
            total_points=100,
        )

        repository = AsyncMock()
        repository.get_by_id.return_value = user
        repository.save = AsyncMock()

        handler = AddPointsHandler(repository)
        command = AddPointsCommand(user_id=user_id, points=50)

        result = await handler(command)

        assert result.user_id == user_id
        assert result.points_added == 50
        assert result.new_total_points == 150
        repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_points_user_not_found(self):
        """Test adding points when user not found."""
        user_id = uuid4()
        repository = AsyncMock()
        repository.get_by_id.return_value = None

        handler = AddPointsHandler(repository)
        command = AddPointsCommand(user_id=user_id, points=50)

        with pytest.raises(UserNotFoundError):
            await handler(command)


class TestUseEnergyHandler:
    """Tests for UseEnergy use case."""

    @pytest.mark.asyncio
    async def test_use_energy_success(self):
        """Test using energy successfully."""
        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=TelegramId(123456789),
            energy=Energy(3),
        )

        repository = AsyncMock()
        repository.get_by_id.return_value = user
        repository.save = AsyncMock()

        handler = UseEnergyHandler(repository)
        command = UseEnergyCommand(user_id=user_id)

        result = await handler(command)

        assert result.user_id == user_id
        assert result.remaining_energy == 2
        assert result.is_depleted is False
        repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_use_energy_when_depleted(self):
        """Test using energy when depleted raises error."""
        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=TelegramId(123456789),
            energy=Energy(0),
        )

        repository = AsyncMock()
        repository.get_by_id.return_value = user

        handler = UseEnergyHandler(repository)
        command = UseEnergyCommand(user_id=user_id)

        with pytest.raises(ValueError, match="No energy left"):
            await handler(command)


class TestRestoreEnergyHandler:
    """Tests for RestoreEnergy use case."""

    @pytest.mark.asyncio
    async def test_restore_energy_success(self):
        """Test restoring energy successfully."""
        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=TelegramId(123456789),
            energy=Energy(1),
        )

        repository = AsyncMock()
        repository.get_by_id.return_value = user
        repository.save = AsyncMock()

        handler = RestoreEnergyHandler(repository)
        command = RestoreEnergyCommand(user_id=user_id)

        result = await handler(command)

        assert result.user_id == user_id
        assert result.current_energy == 5
        assert result.max_energy == 5
        repository.save.assert_called_once()


class TestGetUserProfileHandler:
    """Tests for GetUserProfile query."""

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self):
        """Test getting user profile successfully."""
        user_id = uuid4()
        user = User(
            id=user_id,
            telegram_id=TelegramId(123456789),
            username=Username("john"),
            full_name="John Doe",
            total_points=500,
            energy=Energy(3),
        )

        repository = AsyncMock()
        repository.get_by_id.return_value = user

        handler = GetUserProfileHandler(repository)
        query = GetUserProfileQuery(user_id=user_id)

        result = await handler(query)

        assert result.user_id == user_id
        assert result.telegram_id == 123456789
        assert result.username == "john"
        assert result.full_name == "John Doe"
        assert result.total_points == 500
        assert result.energy == 3
        repository.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self):
        """Test getting user profile when user not found."""
        user_id = uuid4()
        repository = AsyncMock()
        repository.get_by_id.return_value = None

        handler = GetUserProfileHandler(repository)
        query = GetUserProfileQuery(user_id=user_id)

        with pytest.raises(UserNotFoundError):
            await handler(query)
