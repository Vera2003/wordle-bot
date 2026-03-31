"""Stats application layer data transfer objects."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class TopPlayerOutput(BaseModel):
    """Top player in rankings."""
    
    model_config = ConfigDict(from_attributes=True)
    
    telegram_id: int = Field(..., gt=0)
    name: str
    points: int = Field(..., ge=0)


class GameStatsOutput(BaseModel):
    """Game statistics output."""
    
    model_config = ConfigDict(from_attributes=True)
    
    total_games: int = Field(..., ge=0)
    won_games: int = Field(..., ge=0)
    lost_games: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0.0, le=100.0)


class GlobalStatsOutput(BaseModel):
    """Global statistics for the entire system."""
    
    model_config = ConfigDict(from_attributes=True)
    
    total_users: int = Field(..., ge=0)
    total_games: int = Field(..., ge=0)
    won_games: int = Field(..., ge=0)
    lost_games: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0.0, le=100.0)
    total_genes: int = Field(..., ge=0)
    active_genes: int = Field(..., ge=0)
    top_players: list[TopPlayerOutput] = Field(default_factory=list)


class UserStatsOutput(BaseModel):
    """Statistics for a specific user."""
    
    model_config = ConfigDict(from_attributes=True)
    
    telegram_id: int = Field(..., gt=0)
    username: Optional[str] = None
    full_name: Optional[str] = None
    total_points: int = Field(..., ge=0)
    energy: int = Field(..., ge=0)
    game_stats: GameStatsOutput
