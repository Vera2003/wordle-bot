"""Game repository implementation (adapter)."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.game.entities import GameSession, GameAttempt
from src.domain.game.value_objects import Word, LetterStatus, GuessResult
from src.domain.game.repositories import GameRepository
from ..models.game import GameSessionModel, GameAttemptModel


class SQLAlchemyGameRepository(GameRepository):
    """Repository implementation using SQLAlchemy."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, game: GameSession) -> None:
        """Save or update a game session."""
        # Check if game exists
        stmt = select(GameSessionModel).where(GameSessionModel.id == game.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            # Update existing
            model.target_word = game.target_word.value
            model.attempts_count = game.attempt_count
            model.is_won = game.is_won
            model.is_finished = game.is_finished
            model.points_earned = game.points_earned
            model.finished_at = game.finished_at
            model.hint_used = game.hint_used
        else:
            # Create new
            model = GameSessionModel(
                id=game.id,
                user_id=game.user_id,
                target_word=game.target_word.value,
                max_attempts=game.max_attempts,
                attempts_count=game.attempt_count,
                is_won=game.is_won,
                is_finished=game.is_finished,
                points_earned=game.points_earned,
                hint_used=game.hint_used,
            )
            self.session.add(model)
        
        # Save attempts
        self._sync_attempts(game, model)
        
        await self.session.commit()
    
    async def get_by_id(self, game_id: UUID) -> Optional[GameSession]:
        """Get game session by ID."""
        stmt = select(GameSessionModel).where(GameSessionModel.id == game_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def get_active_by_user(self, user_id: UUID) -> Optional[GameSession]:
        """Get active (not finished) game for a user."""
        stmt = (
            select(GameSessionModel)
            .where(
                GameSessionModel.user_id == user_id,
                GameSessionModel.is_finished == False
            )
            .order_by(GameSessionModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def delete(self, game_id: UUID) -> None:
        """Delete a game session."""
        stmt = select(GameSessionModel).where(GameSessionModel.id == game_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            await self.session.delete(model)
            await self.session.commit()
    
    @staticmethod
    def _model_to_entity(model: GameSessionModel) -> GameSession:
        """Convert ORM model to domain entity."""
        game = GameSession(
            id=model.id,
            user_id=model.user_id,
            target_word=Word(model.target_word),
            max_attempts=model.max_attempts,
            created_at=model.created_at,
        )
        
        # Restore attempts
        for attempt_model in model.attempts_history:
            # Reconstruct LetterStatus objects from stored JSON
            result_data = attempt_model.result
            letters = [
                LetterStatus(item["letter"], item["status"])
                for item in result_data
            ]
            
            attempt = GameAttempt(
                id=attempt_model.id,
                attempt_number=attempt_model.attempt_number,
                guess=Word(attempt_model.guess_word),
                result=GuessResult(letters),
                created_at=attempt_model.created_at,
            )
            game._attempts.append(attempt)
        
        # Restore game state
        game._is_won = model.is_won
        game._is_finished = model.is_finished
        game.points_earned = model.points_earned
        game.finished_at = model.finished_at
        game.hint_used = model.hint_used
        
        return game
    
    @staticmethod
    def _sync_attempts(game: GameSession, model: GameSessionModel) -> None:
        """Sync domain attempts to ORM models."""
        # Clear existing attempts
        model.attempts_history.clear()
        
        # Add attempts from domain entity
        for attempt in game.attempts:
            attempt_model = GameAttemptModel(
                id=attempt.id,
                session_id=game.id,
                attempt_number=attempt.attempt_number,
                guess_word=attempt.guess.value,
                result=[
                    {"letter": ls.letter, "status": ls.status}
                    for ls in attempt.result.letters
                ],
                created_at=attempt.created_at,
            )
            model.attempts_history.append(attempt_model)
