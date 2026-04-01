"""Game start command."""

from dataclasses import dataclass
from uuid import UUID

from src.application.game.dto import GameStateOutput
from src.domain.game.entities import GameSession
from src.domain.game.repositories import GameRepository
from src.domain.game.value_objects import Word


@dataclass
class StartGameCommand:
    """Command: start a new game."""

    user_id: UUID
    difficulty: str = "medium"


class StartGameHandler:
    """Handler for StartGameCommand."""

    def __init__(self, game_repo: GameRepository):
        self.game_repo = game_repo

    async def execute(self, cmd: StartGameCommand) -> GameStateOutput:
        """
        Execute start game command.

        Returns:
            GameStateOutput with new game state
        """
        # Check if user has active game
        active_game = await self.game_repo.get_active_by_user(cmd.user_id)
        if active_game:
            # User already has active game
            return self._game_to_output(active_game)

        # Create new game
        # TODO: Get target word based on difficulty from gene service
        target_word = Word("PYTHON")  # Placeholder

        game = GameSession(
            id=UUID(int=0),  # Will be assigned by DB
            user_id=cmd.user_id,
            target_word=target_word,
            max_attempts=6,
        )

        # Save to DB
        await self.game_repo.save(game)

        return self._game_to_output(game)

    @staticmethod
    def _game_to_output(game: GameSession) -> GameStateOutput:
        """Convert domain entity to DTO."""
        return GameStateOutput(
            id=game.id,
            user_id=game.user_id,
            target_word=game.target_word.value,
            attempts=[],  # Should be populated from game.attempts
            attempts_left=game.attempts_left,
            is_won=game.is_won,
            is_lost=game.is_finished and not game.is_won,
            is_finished=game.is_finished,
            total_points=game.points_earned,
            created_at=game.created_at.isoformat(),
        )
