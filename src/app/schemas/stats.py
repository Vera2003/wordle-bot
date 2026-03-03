from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Общие sub-схемы
# ---------------------------------------------------------------------------


class TopPlayerResponse(BaseModel):
    """Один игрок в топ-листе."""

    telegram_id: int
    name: str = Field(..., description="Отображаемое имя (full_name или username)")
    points: int = Field(..., ge=0)


# ---------------------------------------------------------------------------
# GET /api/v1/stats/global
# ---------------------------------------------------------------------------


class GlobalStatsResponse(BaseModel):
    """Ответ глобальной статистики."""

    total_users: int = Field(..., ge=0, description="Всего зарегистрированных пользователей")
    total_games: int = Field(..., ge=0, description="Всего завершённых игр")
    won_games: int = Field(..., ge=0, description="Из них выигранных")
    lost_games: int = Field(..., ge=0, description="Из них проигранных")
    win_rate: float = Field(..., ge=0.0, le=100.0, description="Процент побед (0–100)")
    total_genes: int = Field(..., ge=0, description="Всего генов в базе")
    active_genes: int = Field(..., ge=0, description="Активных генов")
    top_players: list[TopPlayerResponse] = Field(
        default_factory=list,
        description="Топ-10 игроков по очкам",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/stats/user/{telegram_id}
# ---------------------------------------------------------------------------


class UserStatsResponse(BaseModel):
    """Статистика конкретного пользователя."""

    telegram_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    total_points: int = Field(..., ge=0)
    energy: int = Field(..., ge=0)
    total_games: int = Field(..., ge=0)
    won_games: int = Field(..., ge=0)
    lost_games: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0.0, le=100.0)


class UserStatsNotFoundResponse(BaseModel):
    """Ответ когда пользователь не найден."""

    error: str = Field(..., description="Сообщение об ошибке")