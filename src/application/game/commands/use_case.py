"""Game command handlers."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.application.game.dto import (
    GameAttemptDTO,
    GameResultOutput,
    GameStateOutput,
    LetterStatus,
    SubmitGuessOutput,
)
from src.domain.game import GameNotFoundError, GameRepository, GameSession, Word
from src.domain.gene import GeneNotFoundError, GeneRepository, GeneService
from src.domain.user import UserNotFoundError, UserRepository


def _to_attempt_dto(game_attempt) -> GameAttemptDTO:
    return GameAttemptDTO(
        attempt_number=game_attempt.attempt_number,
        guess=game_attempt.guess.value,
        result=[
            LetterStatus(letter=letter.letter, status=letter.status)
            for letter in game_attempt.result.letters
        ],
        is_correct=game_attempt.is_correct(),
        points_earned=0,
    )


def _to_game_state_output(game: GameSession) -> GameStateOutput:
    return GameStateOutput(
        id=game.id,
        user_id=game.user_id,
        target_word=game.target_word.value,
        attempts=[_to_attempt_dto(item) for item in game.attempts],
        attempts_left=game.attempts_left,
        is_won=game.is_won,
        is_lost=game.is_finished and not game.is_won,
        is_finished=game.is_finished,
        total_points=game.points_earned,
        created_at=game.created_at.isoformat(),
    )


def _to_game_result_output(game: GameSession) -> GameResultOutput | None:
    if not game.is_finished:
        return None

    finished_at = game.finished_at or datetime.now()
    duration_seconds = int((finished_at - game.created_at).total_seconds())
    return GameResultOutput(
        game_id=game.id,
        is_won=game.is_won,
        total_attempts=game.attempt_count,
        points_earned=game.points_earned,
        duration_seconds=max(0, duration_seconds),
    )


class StartGameCommand(BaseModel):
    """Command to start a new game session."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    gene_id: UUID | None = None


class StartGameHandler:
    """Handler for StartGame command."""

    def __init__(
        self,
        game_repository: GameRepository,
        gene_repository: GeneRepository,
    ):
        self.game_repository = game_repository
        self.gene_repository = gene_repository

    async def __call__(self, command: StartGameCommand) -> GameStateOutput:
        active_game = await self.game_repository.get_active_by_user(command.user_id)
        if active_game:
            return _to_game_state_output(active_game)

        if command.gene_id is not None:
            gene = await self.gene_repository.get_by_id(command.gene_id)
            if not gene:
                raise GeneNotFoundError(f"Gene {command.gene_id} not found")
        else:
            gene = await self.gene_repository.get_random_active()
            if not gene:
                raise GeneNotFoundError("No active genes available")

        gene.can_be_used()
        game = GameSession(
            id=uuid4(),
            user_id=command.user_id,
            target_word=Word(gene.get_word()),
            max_attempts=GeneService.get_max_attempts_for_difficulty(gene),
        )
        await self.game_repository.save(game)
        return _to_game_state_output(game)


class SubmitGuessCommand(BaseModel):
    """Command to submit a guess for an existing game."""

    model_config = ConfigDict(extra="forbid")

    game_id: UUID
    guess: str = Field(..., min_length=1, max_length=20)


class SubmitGuessHandler:
    """Handler for SubmitGuess command."""

    def __init__(
        self,
        game_repository: GameRepository,
        user_repository: UserRepository,
    ):
        self.game_repository = game_repository
        self.user_repository = user_repository

    async def __call__(self, command: SubmitGuessCommand) -> SubmitGuessOutput:
        game = await self.game_repository.get_by_id(command.game_id)
        if not game:
            raise GameNotFoundError(f"Game {command.game_id} not found")

        game.make_attempt(Word(command.guess, max_length=game.target_word.length()))
        await self.game_repository.save(game)

        if game.is_finished and game.is_won and game.points_earned > 0:
            user = await self.user_repository.get_by_id(game.user_id)
            if not user:
                raise UserNotFoundError(f"User {game.user_id} not found")
            user.add_points(game.points_earned)
            await self.user_repository.save(user)

        game_state = _to_game_state_output(game)
        game_result = _to_game_result_output(game)
        return SubmitGuessOutput(
            game_state=game_state,
            game_finished=game.is_finished,
            game_result=game_result,
        )
