"""Game submit guess command."""

from uuid import UUID
from dataclasses import dataclass

from src.domain.game.value_objects import Word
from src.domain.game.repositories import GameRepository
from src.domain.game.errors import GameError
from src.application.game.dto import (
    GameStateOutput,
    GameAttemptDTO,
    SubmitGuessOutput,
    GameResultOutput,
    LetterStatus,
)


@dataclass
class SubmitGuessCommand:
    """Command: submit a guess for the game."""
    game_id: UUID
    user_id: UUID
    guess: str


class SubmitGuessHandler:
    """Handler for SubmitGuessCommand."""
    
    def __init__(self, game_repo: GameRepository):
        self.game_repo = game_repo
    
    async def execute(self, cmd: SubmitGuessCommand) -> SubmitGuessOutput:
        """
        Execute submit guess command.
        
        Returns:
            SubmitGuessOutput with updated game state
        
        Raises:
            GameError: if game is not found, finished, etc
        """
        # Load game from DB
        game = await self.game_repo.get_by_id(cmd.game_id)
        if not game:
            raise GameError(f"Game {cmd.game_id} not found")
        
        # Make the attempt (this updates game state)
        try:
            attempt = game.make_attempt(Word(cmd.guess))
        except Exception as e:
            raise GameError(f"Invalid guess: {str(e)}")
        
        # Save updated game
        await self.game_repo.save(game)
        
        # Convert to output
        game_state = self._game_to_output(game)
        
        game_result = None
        if game.is_finished:
            game_result = GameResultOutput(
                game_id=game.id,
                is_won=game.is_won,
                total_attempts=game.attempt_count,
                points_earned=game.points_earned,
                duration_seconds=int((game.finished_at - game.created_at).total_seconds()),
            )
        
        return SubmitGuessOutput(
            game_state=game_state,
            game_finished=game.is_finished,
            game_result=game_result,
        )
    
    @staticmethod
    def _game_to_output(game) -> GameStateOutput:
        """Convert domain entity to DTO."""
        attempts = [
            GameAttemptDTO(
                attempt_number=attempt.attempt_number,
                guess=attempt.guess.value,
                result=[
                    LetterStatus(ls.letter, ls.status)
                    for ls in attempt.result.letters
                ],
                is_correct=attempt.is_correct(),
                points_earned=0,  # TODO: Calculate per attempt
            )
            for attempt in game.attempts
        ]
        
        return GameStateOutput(
            id=game.id,
            user_id=game.user_id,
            target_word=game.target_word.value,
            attempts=attempts,
            attempts_left=game.attempts_left,
            is_won=game.is_won,
            is_lost=game.is_finished and not game.is_won,
            is_finished=game.is_finished,
            total_points=game.points_earned,
        )
