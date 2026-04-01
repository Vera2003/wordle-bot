"""Stats domain value objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WinRate:
    """Value object: Win rate percentage (0-100)."""

    value: float

    def __post_init__(self):
        if not (0.0 <= self.value <= 100.0):
            raise ValueError("Win rate must be between 0 and 100")

    def __repr__(self) -> str:
        return f"WinRate({self.value:.2f}%)"


@dataclass(frozen=True)
class GameStats:
    """Value object: Aggregated game statistics."""

    total_games: int
    won_games: int
    lost_games: int
    win_rate: WinRate

    def __post_init__(self):
        if self.total_games < 0:
            raise ValueError("Total games cannot be negative")
        if self.won_games < 0:
            raise ValueError("Won games cannot be negative")
        if self.lost_games < 0:
            raise ValueError("Lost games cannot be negative")
        if self.won_games + self.lost_games != self.total_games:
            raise ValueError("Won + lost games must equal total games")


@dataclass(frozen=True)
class TopPlayer:
    """Value object: Player in top list."""

    telegram_id: int
    name: str
    points: int

    def __post_init__(self):
        if self.telegram_id <= 0:
            raise ValueError("Telegram ID must be positive")
        if self.points < 0:
            raise ValueError("Points cannot be negative")
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty")


@dataclass(frozen=True)
class GlobalStats:
    """Value object: Global statistics for entire system."""

    total_users: int
    total_games: int
    won_games: int
    lost_games: int
    win_rate: WinRate
    total_genes: int
    active_genes: int
    top_players: list[TopPlayer]

    def __post_init__(self):
        if self.total_users < 0:
            raise ValueError("Total users cannot be negative")
        if self.total_genes < 0:
            raise ValueError("Total genes cannot be negative")
        if self.active_genes < 0:
            raise ValueError("Active genes cannot be negative")
        if self.active_genes > self.total_genes:
            raise ValueError("Active genes cannot exceed total genes")
        if self.won_games + self.lost_games != self.total_games:
            raise ValueError("Won + lost games must equal total games")


@dataclass(frozen=True)
class UserStats:
    """Value object: Statistics for a specific user."""

    telegram_id: int
    username: str | None
    full_name: str | None
    total_points: int
    energy: int
    game_stats: GameStats

    def __post_init__(self):
        if self.telegram_id <= 0:
            raise ValueError("Telegram ID must be positive")
        if self.total_points < 0:
            raise ValueError("Total points cannot be negative")
        if self.energy < 0:
            raise ValueError("Energy cannot be negative")
