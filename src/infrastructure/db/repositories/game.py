"""Game repository implementation."""

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.game.entities import GameSession
from src.domain.game.repositories import GameRepository
from src.infrastructure.db.mappers.game import GameMapper
from src.infrastructure.db.models.game import GameSessionModel


class GameRepositoryImpl(GameRepository):
    """SQLAlchemy implementation of GameRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, game: GameSession) -> None:
        """Save a game session."""
        existing = await self.session.get(GameSessionModel, str(game.id))

        if existing:
            updated = GameMapper.domain_to_model(game)
            existing.word = updated.word
            existing.max_attempts = updated.max_attempts
            existing.attempts_count = updated.attempts_count
            existing.is_won = updated.is_won
            existing.is_finished = updated.is_finished
            existing.hint_used = updated.hint_used
            existing.points_earned = updated.points_earned
            existing.finished_at = updated.finished_at
            if updated.attempts_history:
                existing.attempts_history = updated.attempts_history
        else:
            self.session.add(GameMapper.domain_to_model(game))

        await self.session.flush()

    async def get_by_id(self, game_id: UUID) -> Optional[GameSession]:
        """Get game session by ID."""
        result = await self.session.execute(
            select(GameSessionModel)
            .options(selectinload(GameSessionModel.attempts_history))
            .where(GameSessionModel.id == str(game_id))
        )
        model = result.scalars().first()
        return GameMapper.model_to_domain(model) if model else None

    async def get_active_by_user(self, user_id: UUID) -> Optional[GameSession]:
        """Get active game for a user."""
        result = await self.session.execute(
            select(GameSessionModel)
            .options(selectinload(GameSessionModel.attempts_history))
            .where(
                GameSessionModel.user_id == str(user_id),
                GameSessionModel.is_finished.is_(False),
            )
            .order_by(GameSessionModel.created_at.desc())
        )
        model = result.scalars().first()
        return GameMapper.model_to_domain(model) if model else None

    async def get_latest_finished_by_user_and_word(
        self,
        user_id: UUID,
        word: str,
    ) -> Optional[GameSession]:
        """Get the latest finished game for a user and target word."""
        result = await self.session.execute(
            select(GameSessionModel)
            .options(selectinload(GameSessionModel.attempts_history))
            .where(
                GameSessionModel.user_id == str(user_id),
                GameSessionModel.word == word,
                GameSessionModel.is_finished.is_(True),
            )
            .order_by(GameSessionModel.created_at.desc())
            .limit(1)
        )
        model = result.scalars().first()
        return GameMapper.model_to_domain(model) if model else None

    async def has_finished_game_for_user_on_date(
        self,
        user_id: UUID,
        word: str,
        played_on: date,
    ) -> bool:
        """Check whether a user has already finished a game for the word on a day."""
        result = await self.session.execute(
            select(func.count())
            .select_from(GameSessionModel)
            .where(
                GameSessionModel.user_id == str(user_id),
                GameSessionModel.word == word,
                GameSessionModel.is_finished.is_(True),
                func.date(GameSessionModel.created_at) == played_on,
            )
        )
        return bool(result.scalar_one())

    async def delete_by_user(self, user_id: UUID) -> None:
        """Delete all game sessions for a user."""
        await self.session.execute(
            delete(GameSessionModel).where(GameSessionModel.user_id == str(user_id))
        )
        await self.session.flush()

    async def delete(self, game_id: UUID) -> None:
        """Delete a game session."""
        model = await self.session.get(GameSessionModel, str(game_id))
        if model:
            await self.session.delete(model)
            await self.session.flush()


SQLAlchemyGameRepository = GameRepositoryImpl
