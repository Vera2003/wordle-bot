"""Integration tests for GameRepository."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.game.entities import GameSession
from src.domain.game.value_objects import Word
from src.infrastructure.db.models.game import GameSessionModel
from src.infrastructure.db.repositories.game import GameRepositoryImpl


@pytest.mark.asyncio
async def test_game_repository_save_new_game(db):
    """
    Test: Repository can save a new game session.

    Scenario:
    1. Create a GameSession domain entity (no ID in DB yet)
    2. Call repository.save()
    3. Verify it's saved in database

    Why this test matters:
    - Confirms Mapper converts domain → ORM correctly
    - Confirms SQLAlchemy can insert the model
    - Tests the full flow: domain entity → mapper → DB
    """
    repo = GameRepositoryImpl(db)

    # Create a domain entity
    game_id = uuid4()
    user_id = uuid4()
    target_word = Word("PYTHON")
    max_attempts = 6

    game = GameSession(
        id=game_id,
        user_id=user_id,
        target_word=target_word,
        max_attempts=max_attempts,
    )

    # Save via repository
    await repo.save(game)

    # Verify it's in database by querying directly
    db_id = str(game_id)
    model = await db.get(GameSessionModel, db_id)

    assert model is not None
    assert model.word == "PYTHON"
    assert model.max_attempts == 6
    assert model.is_finished is False


@pytest.mark.asyncio
async def test_game_repository_get_by_id(db):
    """
    Test: Repository can retrieve a game by ID.

    Scenario:
    1. Create and save a game
    2. Call repository.get_by_id()
    3. Verify the returned GameSession matches original

    Why this test matters:
    - Tests deserialization: DB row → domain entity
    - Confirms Mapper reconstructs value objects correctly
    - Verifies state is preserved
    """
    repo = GameRepositoryImpl(db)

    # Create and save a game
    game_id = uuid4()
    user_id = uuid4()
    target_word = Word("HELLO")

    original_game = GameSession(
        id=game_id,
        user_id=user_id,
        target_word=target_word,
        max_attempts=6,
    )

    await repo.save(original_game)

    # Retrieve it
    retrieved_game = await repo.get_by_id(game_id)

    # Verify
    assert retrieved_game is not None
    assert retrieved_game.id == game_id
    assert retrieved_game.user_id == user_id
    assert retrieved_game.target_word.value == "HELLO"
    assert retrieved_game.max_attempts == 6
    assert retrieved_game.is_finished is False
    assert retrieved_game.is_won is False


@pytest.mark.asyncio
async def test_game_repository_get_active_by_user(db):
    """
    Test: Repository returns only active game for a user.

    Scenario:
    1. Create two games for same user: one active, one finished
    2. Call repository.get_active_by_user()
    3. Should return only the active one

    Why this test matters:
    - Tests business logic: filtering for active games
    - Confirms query is correct
    - Verifies finished games are excluded

    Database business rule:
    - A user can have multiple games (finished + active)
    - But only ONE active game at a time
    - Repository enforces this
    """
    repo = GameRepositoryImpl(db)

    user_id = uuid4()

    # Create first game and finish it
    game1 = GameSession(
        id=uuid4(),
        user_id=user_id,
        target_word=Word("FIRST"),
        max_attempts=6,
    )
    game1._is_finished = True  # Mark as finished
    game1._is_won = True
    game1.finished_at = datetime.now()

    await repo.save(game1)

    # Create second game (active)
    game2 = GameSession(
        id=uuid4(),
        user_id=user_id,
        target_word=Word("SECOND"),
        max_attempts=6,
    )
    # game2 is NOT finished (by default)

    await repo.save(game2)

    # Get active game
    active_game = await repo.get_active_by_user(user_id)

    # Should get game2 (the active one)
    assert active_game is not None
    assert active_game.id == game2.id
    assert active_game.is_finished is False


@pytest.mark.asyncio
async def test_game_repository_get_nonexistent_returns_none(db):
    """
    Test: Repository returns None for non-existent game.

    Scenario:
    1. Try to get a game with ID that never existed
    2. Should return None gracefully

    Why this test matters:
    - Error handling: what if game doesn't exist?
    - Should not raise exception, just return None
    - Use case will handle the None appropriately
    """
    repo = GameRepositoryImpl(db)

    non_existent_id = uuid4()
    result = await repo.get_by_id(non_existent_id)

    assert result is None


@pytest.mark.asyncio
async def test_game_repository_update_game(db):
    """
    Test: Repository can update an existing game.

    Scenario:
    1. Create and save a game
    2. Modify it (make attempt, increment points, finish it)
    3. Save again (should update, not insert)
    4. Verify changes in database

    Why this test matters:
    - Tests UPDATE path in save() method
    - Confirms we don't create duplicate records
    - Verifies state changes are persisted
    """
    repo = GameRepositoryImpl(db)

    # Create and save
    game_id = uuid4()
    user_id = uuid4()

    game = GameSession(
        id=game_id,
        user_id=user_id,
        target_word=Word("TEST"),
        max_attempts=6,
    )

    await repo.save(game)

    # Modify the game
    game._is_finished = True
    game._is_won = True
    game.points_earned = 100
    game.finished_at = datetime.now()

    # Save again (should update)
    await repo.save(game)

    # Retrieve and verify
    updated_game = await repo.get_by_id(game_id)

    assert updated_game is not None
    assert updated_game.is_finished is True
    assert updated_game.is_won is True
    assert updated_game.points_earned == 100
