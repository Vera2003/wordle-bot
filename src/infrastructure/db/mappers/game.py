"""Mappers for converting ORM models to/from domain objects."""

from uuid import UUID
from src.domain.game.entities import GameSession, GameAttempt
from src.domain.game.value_objects import Word, GuessResult, LetterStatus
from src.infrastructure.db.models.game import GameSessionModel, GameAttemptModel


class GameMapper:
    """
    Mapper for GameSession: ORM Model <-> Domain Entity.
    
    This class is responsible for converting between:
    - GameSessionModel (what we store in PostgreSQL)
    - GameSession (what we use in business logic)
    
    Why a mapper?
    - ORM Models know about DB: columns, relationships, SQL
    - Domain Entities know about business: rules, validations, behavior
    - They serve different purposes, so we need a translator
    """
    
    @staticmethod
    def model_to_domain(model: GameSessionModel) -> GameSession:
        """
        Convert SQLAlchemy GameSessionModel to domain GameSession entity.
        
        Args:
            model: GameSessionModel from database
            
        Returns:
            GameSession domain entity with all attempts loaded
            
        What happens here:
        1. Reconstruct the target word from the model
        2. Create GameSession with basic properties
        3. Load all attempts from the relationship
        4. Restore the game state (won/finished flags)
        """
        # Reconstruct UUID from hex string stored in DB
        game_id = UUID(model.id)
        user_id = UUID(model.user_id)
        
        # Create the main game session
        game = GameSession(
            id=game_id,
            user_id=user_id,
            target_word=Word(model.word),  # Wrap string in Word value object
            max_attempts=model.max_attempts,
            created_at=model.created_at,
        )
        
        # Restore the game state from the model
        game._is_won = model.is_won
        game._is_finished = model.is_finished
        game.finished_at = model.finished_at
        game.points_earned = model.points_earned
        game.hint_used = model.hint_used
        
        attempts = sorted(model.attempts_history, key=lambda item: item.attempt_number)
        for attempt_model in attempts:
            game._attempts.append(GameMapper._model_attempt_to_domain(attempt_model))
        
        return game
    
    @staticmethod
    def domain_to_model(game: GameSession) -> GameSessionModel:
        """
        Convert domain GameSession entity to SQLAlchemy GameSessionModel.
        
        Args:
            game: GameSession domain entity
            
        Returns:
            GameSessionModel ready to save to database
            
        What happens here:
        1. Extract all properties from domain entity
        2. Extract value objects (Word → string)
        3. Create ORM model with all data
        4. Convert attempts too
        """
        # Convert UUID to hex string for DB storage
        model = GameSessionModel(
            id=str(game.id),  #UUID as hex string (36 chars with hyphens)
            user_id=str(game.user_id),  # UUID as hex string
            word=game.target_word.value,  # Extract string from Word VO
            max_attempts=game.max_attempts,
            attempts_count=game.attempt_count,  # Read-only property
            is_won=game.is_won,
            is_finished=game.is_finished,
            finished_at=game.finished_at,
            points_earned=game.points_earned,
            hint_used=game.hint_used,
            created_at=game.created_at,
        )
        
        # Convert all attempts
        if game.attempts:
            model.attempts_history = [
                GameMapper._domain_attempt_to_model(attempt)
                for attempt in game.attempts
            ]
        
        return model
    
    @staticmethod
    def _model_attempt_to_domain(model: GameAttemptModel) -> GameAttempt:
        """
        Convert GameAttemptModel to domain GameAttempt.
        
        Internal helper method for loading attempts from DB.
        """
        # Reconstruct UUID from hex string
        attempt_id = UUID(model.id)
        
        # Reconstruct the GuessResult from the JSON stored in DB
        result = GameMapper._reconstruct_guess_result(model.result)
        
        return GameAttempt(
            id=attempt_id,
            attempt_number=model.attempt_number,
            guess=Word(model.guess_word),
            result=result,
            created_at=model.created_at,
        )
    
    @staticmethod
    def _domain_attempt_to_model(attempt: GameAttempt) -> GameAttemptModel:
        """
        Convert domain GameAttempt to GameAttemptModel.
        
        Internal helper method for saving attempts to DB.
        """
        return GameAttemptModel(
            id=str(attempt.id),  # UUID as hex string
            attempt_number=attempt.attempt_number,
            guess_word=attempt.guess.value,
            result=GameMapper._guess_result_to_dict(attempt.result),
            created_at=attempt.created_at,
        )
    
    @staticmethod
    def _guess_result_to_dict(result: GuessResult) -> dict:
        """
        Convert GuessResult value object to JSON-serializable dict for DB storage.
        
        GuessResult contains LetterStatus objects which aren't JSON-serializable,
        so we convert to plain dicts.
        """
        return {
            "letters": [
                {
                    "letter": letter.letter,
                    "status": letter.status
                }
                for letter in result.letters
            ]
        }
    
    @staticmethod
    def _reconstruct_guess_result(data: dict) -> GuessResult:
        """
        Reconstruct GuessResult value object from JSON dict stored in DB.
        
        Reverse of _guess_result_to_dict.
        """
        letters = [
            LetterStatus(
                letter=letter_data["letter"],
                status=letter_data["status"]
            )
            for letter_data in data.get("letters", [])
        ]
        return GuessResult(letters)
