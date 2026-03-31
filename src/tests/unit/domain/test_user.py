"""Unit tests for User domain."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.domain.user import (
    User,
    TelegramId,
    Username,
    Energy,
    UserNotFoundError,
    InvalidTelegramIdError,
    InvalidUsernameError,
)


class TestTelegramId:
    """Tests for TelegramId value object."""
    
    def test_creation_valid(self):
        """Test creating TelegramId with valid value."""
        tg_id = TelegramId(123456789)
        assert tg_id.value == 123456789
    
    def test_creation_invalid_negative(self):
        """Test creating TelegramId with negative value."""
        with pytest.raises(ValueError):
            TelegramId(-1)
    
    def test_creation_invalid_zero(self):
        """Test creating TelegramId with zero."""
        with pytest.raises(ValueError):
            TelegramId(0)
    
    def test_creation_invalid_type(self):
        """Test creating TelegramId with non-integer."""
        with pytest.raises(ValueError):
            TelegramId("123456789")
    
    def test_equality(self):
        """Test TelegramId equality."""
        id1 = TelegramId(123456789)
        id2 = TelegramId(123456789)
        id3 = TelegramId(987654321)
        
        assert id1 == id2
        assert id1 != id3
    
    def test_hashing(self):
        """Test TelegramId hashing."""
        id1 = TelegramId(123456789)
        id2 = TelegramId(123456789)
        
        assert hash(id1) == hash(id2)
        # Can be used in sets
        s = {id1, id2}
        assert len(s) == 1


class TestUsername:
    """Tests for Username value object."""
    
    def test_creation_valid(self):
        """Test creating Username with valid value."""
        username = Username("john_doe")
        assert username.value == "john_doe"
    
    def test_creation_none(self):
        """Test creating Username with None."""
        username = Username(None)
        assert username.value is None
    
    def test_creation_too_short(self):
        """Test creating Username with empty string."""
        with pytest.raises(ValueError):
            Username("")
    
    def test_creation_too_long(self):
        """Test creating Username over 32 characters."""
        with pytest.raises(ValueError):
            Username("a" * 33)
    
    def test_creation_invalid_type(self):
        """Test creating Username with non-string."""
        with pytest.raises(ValueError):
            Username(123)
    
    def test_equality(self):
        """Test Username equality."""
        u1 = Username("john")
        u2 = Username("john")
        u3 = Username("jane")
        
        assert u1 == u2
        assert u1 != u3


class TestEnergy:
    """Tests for Energy value object."""
    
    def test_creation_valid(self):
        """Test creating Energy with valid value."""
        energy = Energy(3, max_energy=5)
        assert energy.value == 3
        assert energy.max == 5
    
    def test_creation_default_max(self):
        """Test Energy defaults to max 5."""
        energy = Energy(3)
        assert energy.max == 5
    
    def test_creation_invalid_negative(self):
        """Test creating Energy with negative value."""
        with pytest.raises(ValueError):
            Energy(-1)
    
    def test_creation_exceeds_max(self):
        """Test creating Energy exceeding max."""
        with pytest.raises(ValueError):
            Energy(10, max_energy=5)
    
    def test_is_depleted(self):
        """Test checking energy depletion."""
        empty = Energy(0)
        full = Energy(5)
        
        assert empty.is_depleted()
        assert not full.is_depleted()
    
    def test_is_full(self):
        """Test checking if energy is full."""
        full = Energy(5)
        partial = Energy(3)
        
        assert full.is_full()
        assert not partial.is_full()
    
    def test_use_energy(self):
        """Test using one energy point."""
        energy = Energy(3)
        new_energy = energy.use_energy()
        
        assert new_energy.value == 2
        # Original energy unchanged (immutable)
        assert energy.value == 3
    
    def test_use_energy_when_depleted(self):
        """Test using energy when depleted raises error."""
        energy = Energy(0)
        with pytest.raises(ValueError, match="No energy left"):
            energy.use_energy()
    
    def test_restore(self):
        """Test restoring energy to full."""
        energy = Energy(2, max_energy=5)
        restored = energy.restore()
        
        assert restored.value == 5
        assert restored.is_full()


class TestUser:
    """Tests for User aggregate root."""
    
    @pytest.fixture
    def user_id(self):
        return uuid4()
    
    @pytest.fixture
    def default_user(self, user_id):
        """Create a test user with defaults."""
        return User(
            id=user_id,
            telegram_id=TelegramId(123456789),
        )
    
    def test_creation_with_defaults(self, default_user):
        """Test creating user with default values."""
        assert default_user.telegram_id.value == 123456789
        assert default_user.username.value is None
        assert default_user.full_name is None
        assert default_user.energy.value == 5  # Default energy
        assert default_user.total_points == 0
    
    def test_creation_with_custom_values(self, user_id):
        """Test creating user with custom values."""
        username = Username("john_doe")
        energy = Energy(3, max_energy=5)
        
        user = User(
            id=user_id,
            telegram_id=TelegramId(123456789),
            username=username,
            full_name="John Doe",
            energy=energy,
            total_points=100,
        )
        
        assert user.username == username
        assert user.full_name == "John Doe"
        assert user.energy.value == 3
        assert user.total_points == 100
    
    def test_add_points(self, default_user):
        """Test adding points to user."""
        default_user.add_points(50)
        assert default_user.total_points == 50
        
        default_user.add_points(25)
        assert default_user.total_points == 75
    
    def test_add_points_negative_raises(self, default_user):
        """Test adding negative points raises error."""
        with pytest.raises(ValueError):
            default_user.add_points(-10)
    
    def test_use_energy(self, default_user):
        """Test using energy."""
        assert default_user.energy.value == 5
        
        default_user.use_energy()
        assert default_user.energy.value == 4
        
        default_user.use_energy()
        assert default_user.energy.value == 3
    
    def test_use_energy_depleted_raises(self):
        """Test using energy when depleted raises error."""
        user = User(
            id=uuid4(),
            telegram_id=TelegramId(123456789),
            energy=Energy(0),
        )
        
        with pytest.raises(ValueError, match="No energy left"):
            user.use_energy()
    
    def test_restore_energy(self):
        """Test restoring energy."""
        user = User(
            id=uuid4(),
            telegram_id=TelegramId(123456789),
            energy=Energy(2),
        )
        
        user.restore_energy()
        assert user.energy.is_full()
        assert user.energy.value == 5
    
    def test_update_profile(self, default_user):
        """Test updating user profile."""
        new_username = Username("jane_doe")
        
        default_user.update_profile(
            username=new_username,
            full_name="Jane Doe"
        )
        
        assert default_user.username == new_username
        assert default_user.full_name == "Jane Doe"
    
    def test_equality(self, user_id):
        """Test user equality based on ID."""
        user1 = User(id=user_id, telegram_id=TelegramId(111111111))
        user2 = User(id=user_id, telegram_id=TelegramId(222222222))
        user3 = User(id=uuid4(), telegram_id=TelegramId(111111111))
        
        # Same ID = same user
        assert user1 == user2
        # Different ID = different user
        assert user1 != user3
    
    def test_hashing(self, user_id):
        """Test user can be hashed."""
        user1 = User(id=user_id, telegram_id=TelegramId(111111111))
        user2 = User(id=user_id, telegram_id=TelegramId(222222222))
        
        # Can be used in sets
        s = {user1, user2}
        assert len(s) == 1
    
    def test_updated_at_changes(self, default_user):
        """Test updated_at timestamp changes on modifications."""
        original_time = default_user.updated_at
        
        # Wait a tiny bit for time to pass
        import time
        time.sleep(0.01)
        
        default_user.add_points(10)
        assert default_user.updated_at > original_time
