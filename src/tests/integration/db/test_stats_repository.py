"""Integration tests for Stats repository."""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.infrastructure.db.base import Base
from src.infrastructure.db.models.game import GameSessionModel
from src.infrastructure.db.models.gene import GeneModel
from src.infrastructure.db.models.user import UserModel
from src.infrastructure.db.repositories.stats import StatsRepositoryImpl
from src.domain.stats import UserNotFoundError


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database session for testing."""
    # Patch BigInteger for SQLite
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
    setattr(SQLiteTypeCompiler, "visit_big_integer", lambda self, type_, **kw: "INTEGER")
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    factory = async_sessionmaker(engine, expire_on_commit=False)
    
    async with factory() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


class TestStatsRepositoryGlobalStats:
    """Tests for StatsRepository.get_global_stats()."""
    
    @pytest.mark.asyncio
    async def test_global_stats_empty_system(self, db_session: AsyncSession):
        """Test global stats with empty system."""
        repository = StatsRepositoryImpl(db_session)
        
        stats = await repository.get_global_stats()
        
        assert stats.total_users == 0
        assert stats.total_games == 0
        assert stats.won_games == 0
        assert stats.lost_games == 0
        assert stats.total_genes == 0
        assert stats.active_genes == 0
        assert len(stats.top_players) == 0
        assert stats.win_rate.value == 0.0
    
    @pytest.mark.asyncio
    async def test_global_stats_with_data(self, db_session: AsyncSession):
        """Test global stats with users and games."""
        # Create genes
        gene1 = GeneModel(name="GENE1", description="Test gene 1", hint="Hint 1", is_active=True)
        gene2 = GeneModel(name="GENE2", description="Test gene 2", hint="Hint 2", is_active=False)
        db_session.add_all([gene1, gene2])
        await db_session.flush()
        
        # Create users
        user1 = UserModel(
            id=uuid4(),
            telegram_id=111111111,
            username="alice",
            full_name="Alice",
            energy=5,
            total_points=1000,
        )
        user2 = UserModel(
            id=uuid4(),
            telegram_id=222222222,
            username="bob",
            full_name="Bob",
            energy=3,
            total_points=800,
        )
        db_session.add_all([user1, user2])
        await db_session.flush()
        
        # Create games
        game1 = GameSessionModel(
            user_id=user1.id,
            word=gene1.name,
            is_won=True,
            is_finished=True,
            attempts_count=3,
            points_earned=100,
            finished_at=datetime.utcnow(),
        )
        game2 = GameSessionModel(
            user_id=user1.id,
            word=gene2.name,
            is_won=False,
            is_finished=True,
            attempts_count=6,
            points_earned=0,
            finished_at=datetime.utcnow(),
        )
        game3 = GameSessionModel(
            user_id=user2.id,
            word=gene1.name,
            is_won=True,
            is_finished=True,
            attempts_count=2,
            points_earned=120,
            finished_at=datetime.utcnow(),
        )
        db_session.add_all([game1, game2, game3])
        await db_session.commit()
        
        # Get stats
        repository = StatsRepositoryImpl(db_session)
        stats = await repository.get_global_stats()
        
        # Verify global stats
        assert stats.total_users == 2
        assert stats.total_games == 3
        assert stats.won_games == 2
        assert stats.lost_games == 1
        assert stats.win_rate.value == 66.67
        assert stats.total_genes == 2
        assert stats.active_genes == 1
        
        # Verify top players (Alice has 1000 points, Bob has 800)
        assert len(stats.top_players) == 2
        assert stats.top_players[0].telegram_id == 111111111
        assert stats.top_players[0].name == "Alice"
        assert stats.top_players[0].points == 1000
        assert stats.top_players[1].telegram_id == 222222222
        assert stats.top_players[1].name == "Bob"
        assert stats.top_players[1].points == 800


class TestStatsRepositoryUserStats:
    """Tests for StatsRepository.get_user_stats()."""
    
    @pytest.mark.asyncio
    async def test_user_stats_success(self, db_session: AsyncSession):
        """Test getting user stats successfully."""
        # Create gene
        gene = GeneModel(name="GENE1", description="Test", hint="Hint", is_active=True)
        db_session.add(gene)
        await db_session.flush()
        
        # Create user
        user = UserModel(
            id=uuid4(),
            telegram_id=123456789,
            username="john",
            full_name="John Doe",
            energy=2,
            total_points=500,
        )
        db_session.add(user)
        await db_session.flush()
        
        # Create games
        game1 = GameSessionModel(
            user_id=user.id,
            word=gene.name,
            is_won=True,
            is_finished=True,
            attempts_count=2,
            points_earned=100,
            finished_at=datetime.utcnow(),
        )
        game2 = GameSessionModel(
            user_id=user.id,
            word=gene.name,
            is_won=False,
            is_finished=True,
            attempts_count=6,
            points_earned=0,
            finished_at=datetime.utcnow(),
        )
        db_session.add_all([game1, game2])
        await db_session.commit()
        
        # Get user stats
        repository = StatsRepositoryImpl(db_session)
        stats = await repository.get_user_stats(123456789)
        
        # Verify user info
        assert stats.telegram_id == 123456789
        assert stats.username == "john"
        assert stats.full_name == "John Doe"
        assert stats.total_points == 500
        assert stats.energy == 2
        
        # Verify game stats
        assert stats.game_stats.total_games == 2
        assert stats.game_stats.won_games == 1
        assert stats.game_stats.lost_games == 1
        assert stats.game_stats.win_rate.value == 50.0
    
    @pytest.mark.asyncio
    async def test_user_stats_not_found(self, db_session: AsyncSession):
        """Test getting stats for nonexistent user."""
        repository = StatsRepositoryImpl(db_session)
        
        with pytest.raises(UserNotFoundError):
            await repository.get_user_stats(999999999)
    
    @pytest.mark.asyncio
    async def test_user_stats_no_games(self, db_session: AsyncSession):
        """Test user stats with no games played."""
        user = UserModel(
            id=uuid4(),
            telegram_id=123456789,
            username="new_user",
            full_name="New User",
            energy=5,
            total_points=0,
        )
        db_session.add(user)
        await db_session.commit()
        
        repository = StatsRepositoryImpl(db_session)
        stats = await repository.get_user_stats(123456789)
        
        assert stats.telegram_id == 123456789
        assert stats.game_stats.total_games == 0
        assert stats.game_stats.won_games == 0
        assert stats.game_stats.lost_games == 0
        assert stats.game_stats.win_rate.value == 0.0
