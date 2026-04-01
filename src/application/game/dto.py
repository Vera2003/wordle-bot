"""Game domain DTOs - input and output for game operations."""

from typing import List, Literal, Optional
from uuid import UUID

from pydantic import Field

from ..common.dto import BaseDTO


class LetterStatus(BaseDTO):
    """Статус буквы в попытке (игровая логика)."""

    letter: str = Field(..., description="Буква")
    status: Literal["correct", "present", "absent"] = Field(
        ..., description="correct=на месте, present=есть но не тут, absent=нет в слове"
    )


class GameAttemptDTO(BaseDTO):
    """Попытка отгадать слово."""

    attempt_number: int = Field(..., ge=1, description="Номер попытки (1 = первая)")
    guess: str = Field(..., min_length=1, description="Введенное слово")
    result: List[LetterStatus] = Field(..., description="Результат проверки букв")
    is_correct: bool = Field(..., description="Слово полностью угадано?")
    points_earned: int = Field(
        default=0, ge=0, description="Заработано очков за эту попытку"
    )


# === COMMAND INPUT DTOs (для изменения состояния) ===


class StartGameInput(BaseDTO):
    """Input для команды 'начать новую игру'."""

    user_id: UUID = Field(..., description="ID пользователя")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium", description="Сложность игры"
    )


class SubmitGuessInput(BaseDTO):
    """Input для команды 'отправить попытку угадать'."""

    game_id: UUID = Field(..., description="ID текущей игры")
    guess: str = Field(
        ..., min_length=1, max_length=20, description="Угадываемое слово"
    )


class FinishGameInput(BaseDTO):
    """Input для команды 'закончить игру'."""

    game_id: UUID = Field(..., description="ID игры")
    user_id: UUID = Field(..., description="ID пользователя")


# === QUERY INPUT DTOs (для получения информации) ===


class GetGameStateInput(BaseDTO):
    """Input для запроса текущего состояния игры."""

    game_id: UUID = Field(..., description="ID игры")


class GetGameHistoryInput(BaseDTO):
    """Input для запроса истории игр."""

    user_id: UUID = Field(..., description="ID пользователя")
    offset: int = Field(default=0, ge=0, description="Сколько пропустить")
    limit: int = Field(default=20, ge=1, le=100, description="Сколько вернуть")


# === OUTPUT DTOs (ответы) ===


class GameStateOutput(BaseDTO):
    """Текущее состояние игры."""

    id: UUID = Field(..., description="ID игры")
    user_id: UUID = Field(..., description="ID пользователя")
    target_word: str = Field(
        ..., description="Загаданное слово"
    )  # На клиент не отправляется!
    attempts: List[GameAttemptDTO] = Field(
        default_factory=list, description="История попыток"
    )
    attempts_left: int = Field(..., ge=0, description="Осталось попыток")
    is_won: bool = Field(..., description="Игра выиграна?")
    is_lost: bool = Field(..., description="Игра проиграна?")
    is_finished: bool = Field(..., description="Игра закончена?")
    total_points: int = Field(default=0, ge=0, description="Всего заработано очков")
    created_at: Optional[str] = Field(None, description="Когда создана игра")


class GameResultOutput(BaseDTO):
    """Результат завершенной игры."""

    game_id: UUID = Field(..., description="ID игры")
    is_won: bool = Field(..., description="Результат: победа?")
    total_attempts: int = Field(..., description="Всего попыток")
    points_earned: int = Field(..., ge=0, description="Заработано очков")
    duration_seconds: int = Field(..., ge=0, description="Длительность игры в секундах")


class GameListItemOutput(BaseDTO):
    """Элемент списка игр (для истории)."""

    id: UUID = Field(..., description="ID игры")
    user_id: UUID = Field(..., description="ID пользователя")
    is_won: bool = Field(..., description="Победа?")
    total_attempts: int = Field(..., description="Попыток")
    points_earned: int = Field(..., ge=0, description="Очков")
    created_at: Optional[str] = Field(None, description="Когда создана игра")


class SubmitGuessOutput(BaseDTO):
    """Output команды 'отправить попытку'."""

    game_state: GameStateOutput = Field(..., description="Обновленное состояние игры")
    game_finished: bool = Field(..., description="Игра закончена после этой попытки?")
    game_result: Optional[GameResultOutput] = Field(
        None, description="Результат (если игра закончилась)"
    )
