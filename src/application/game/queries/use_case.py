"""Game query handlers."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.application.game.commands.use_case import _to_game_state_output
from src.application.game.dto import GameStateOutput
from src.domain.game import GameNotFoundError, GameRepository


class GetGameByIdQuery(BaseModel):
    """Query to fetch a game session by ID."""

    model_config = ConfigDict(extra="forbid")

    game_id: UUID


class GetGameByIdHandler:
    """Handler for GetGameById query."""

    def __init__(self, game_repository: GameRepository):
        self.game_repository = game_repository

    async def __call__(self, query: GetGameByIdQuery) -> GameStateOutput:
        game = await self.game_repository.get_by_id(query.game_id)
        if not game:
            raise GameNotFoundError(f"Game {query.game_id} not found")
        return _to_game_state_output(game)


class GetActiveGameByUserQuery(BaseModel):
    """Query to fetch an active game by user ID."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID


class GetActiveGameByUserHandler:
    """Handler for GetActiveGameByUser query."""

    def __init__(self, game_repository: GameRepository):
        self.game_repository = game_repository

    async def __call__(self, query: GetActiveGameByUserQuery) -> GameStateOutput | None:
        game = await self.game_repository.get_active_by_user(query.user_id)
        if game is None:
            return None
        return _to_game_state_output(game)
