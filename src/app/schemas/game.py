from pydantic import BaseModel, Field
from typing import List, Literal


class LetterStatus(BaseModel):
    """Статус буквы в попытке"""
    letter: str = Field(..., description="Буква")
    status: Literal["correct", "present", "absent"] = Field(
        ..., 
        description="correct=на месте, present=есть но не тут, absent=нет в слове"
    )


class AttemptResult(BaseModel):
    """Результат попытки угадывания"""
    attempt_number: int = Field(..., description="Номер попытки")
    guess: str = Field(..., description="Введенное слово")
    result: List[LetterStatus] = Field(..., description="Результат проверки")
    is_correct: bool = Field(..., description="Слово угадано полностью?")
    is_game_over: bool = Field(..., description="Игра завершена?")
    is_won: bool = Field(..., description="Игра выиграна?")
    attempts_left: int = Field(..., description="Осталось попыток")
    points_earned: int = Field(default=0, description="Заработано очков")


class GameStats(BaseModel):
    """Статистика игр пользователя"""
    total_games: int
    won_games: int
    lost_games: int
    win_rate: float
    total_points: int
