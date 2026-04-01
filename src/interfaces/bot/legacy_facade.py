"""Bridge layer that preserves the bot-facing contract on top of the refactored stack."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.game.commands.use_case import (
    StartGameCommand,
    StartGameHandler,
    SubmitGuessCommand,
    SubmitGuessHandler,
)
from src.application.game.dto import SubmitGuessOutput
from src.application.gene import (
    ActivateGeneCommand,
    ActivateGeneHandler,
    CreateGeneCommand,
    CreateGeneHandler,
    DeactivateGeneCommand,
    DeactivateGeneHandler,
    GetGeneByIdHandler,
    GetGeneByIdQuery,
    ListGenesHandler,
    ListGenesQuery,
    UpdateGeneCommand,
    UpdateGeneHandler,
)
from src.application.gene.dto import GeneOutput
from src.application.llm.commands.use_case import (
    AskGeneticsQuestionCommand,
    AskGeneticsQuestionHandler,
    ChatHistoryItem,
    GenerateGeneFactCommand,
    GenerateGeneFactHandler,
)
from src.application.stats import (
    GetGlobalStatsHandler,
    GetGlobalStatsQuery,
    GetUserStatsHandler,
    GetUserStatsQuery,
)
from src.application.stats.dto import GlobalStatsOutput, UserStatsOutput
from src.application.user.commands.get_or_create_user import (
    GetOrCreateUserCommand,
    GetOrCreateUserHandler,
)
from src.domain.game.entities import GameSession
from src.domain.prize import Prize, PrizeValue
from src.domain.user import TelegramId, User
from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.repositories.achievement import UserAchievementRepositoryImpl
from src.infrastructure.db.repositories.game import GameRepositoryImpl
from src.infrastructure.db.repositories.gene import GeneRepositoryImpl
from src.infrastructure.db.repositories.llm import LLMLogRepositoryImpl
from src.infrastructure.db.repositories.prize import (
    PrizeRepositoryImpl,
    UserPrizeRepositoryImpl,
)
from src.infrastructure.db.repositories.stats import StatsRepositoryImpl
from src.infrastructure.db.repositories.user import UserRepositoryImpl
from src.infrastructure.llm.proxyapi_service import ProxyApiLLMService
from src.utils.time_helpers import (
    get_seconds_until_midnight,
    get_today_date,
    get_today_str,
)

settings = get_settings()
_ENERGY_CACHE_TTL = 3600
_DIFFICULTY_EMOJI = {
    "easy": "🟢 Лёгкая",
    "medium": "🟡 Средняя",
    "hard": "🔴 Сложная",
}


@dataclass(frozen=True)
class BotUser:
    """User view consumed by bot handlers."""

    id: UUID
    telegram_id: int
    username: str | None
    full_name: str | None
    total_points: int


@dataclass(frozen=True)
class BotGene:
    """Gene view consumed by bot handlers."""

    id: str
    name: str
    description: str
    hint: str
    difficulty: str
    is_active: bool


@dataclass(frozen=True)
class BotGameSession:
    """Game session view consumed by bot handlers."""

    id: str
    user_id: UUID
    gene_id: str
    attempts: int
    max_attempts: int
    is_won: bool
    is_finished: bool
    hint_used: bool
    points_earned: int
    started_at: datetime
    finished_at: datetime | None
    gene: BotGene


@dataclass(frozen=True)
class BotAttemptLetter:
    """Single letter status for a guess attempt."""

    letter: str
    status: str


@dataclass(frozen=True)
class BotAttemptResult:
    """Guess result returned to bot handlers."""

    attempt_number: int
    guess: str
    result: list[BotAttemptLetter]
    is_correct: bool
    is_game_over: bool
    is_won: bool
    attempts_left: int
    points_earned: int


@dataclass(frozen=True)
class BotPrize:
    """Prize view consumed by admin handlers."""

    id: str
    name: str
    title: str
    description: str
    prize_value: str
    is_active: bool


def _parse_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _energy_cache_key(user_id: UUID | str) -> str:
    return f"user:{user_id}:energy"


def _daily_hint_key(user_id: UUID | str) -> str:
    return f"user:{user_id}:daily_hints:{get_today_str()}"


def _gene_of_day_key() -> str:
    return f"gene_of_day:{get_today_str()}"


def _to_bot_user(user: User | None) -> BotUser | None:
    if user is None:
        return None
    return BotUser(
        id=user.id,
        telegram_id=user.telegram_id.value,
        username=user.username.value if user.username else None,
        full_name=user.full_name,
        total_points=user.total_points,
    )


def _gene_output_to_bot_gene(gene: GeneOutput) -> BotGene:
    return BotGene(
        id=gene.id.hex,
        name=gene.name,
        description=gene.description,
        hint=gene.hint,
        difficulty=gene.difficulty,
        is_active=gene.is_active,
    )


def _prize_to_bot(prize: Prize) -> BotPrize:
    return BotPrize(
        id=prize.id.hex,
        name=prize.name,
        title=prize.title,
        description=prize.description,
        prize_value=prize.value.value,
        is_active=prize.is_active,
    )


async def _resolve_bot_gene(
    gene_repository: GeneRepositoryImpl,
    word: str,
) -> BotGene:
    gene = await gene_repository.get_by_name(word)
    if gene is None:
        return BotGene(
            id="",
            name=word,
            description="",
            hint="",
            difficulty="medium",
            is_active=False,
        )
    return BotGene(
        id=gene.id.hex,
        name=gene.name.value,
        description=gene.description,
        hint=gene.hint,
        difficulty=gene.difficulty.level,
        is_active=gene.is_active,
    )


async def _game_to_bot_session(
    game: GameSession,
    gene_repository: GeneRepositoryImpl,
    resolved_gene: BotGene | None = None,
) -> BotGameSession:
    gene = resolved_gene or await _resolve_bot_gene(
        gene_repository, game.target_word.value
    )
    return BotGameSession(
        id=game.id.hex,
        user_id=game.user_id,
        gene_id=gene.id,
        attempts=game.attempt_count,
        max_attempts=game.max_attempts,
        is_won=game.is_won,
        is_finished=game.is_finished,
        hint_used=game.hint_used,
        points_earned=game.points_earned,
        started_at=game.created_at,
        finished_at=game.finished_at,
        gene=gene,
    )


def _submit_guess_output_to_bot_result(result: SubmitGuessOutput) -> BotAttemptResult:
    attempt = result.game_state.attempts[-1]
    points_earned = result.game_result.points_earned if result.game_result else 0
    return BotAttemptResult(
        attempt_number=attempt.attempt_number,
        guess=attempt.guess,
        result=[
            BotAttemptLetter(letter=item.letter, status=item.status)
            for item in attempt.result
        ],
        is_correct=attempt.is_correct,
        is_game_over=result.game_finished,
        is_won=result.game_result.is_won if result.game_result else False,
        attempts_left=result.game_state.attempts_left,
        points_earned=points_earned,
    )


async def _restore_energy_if_needed(
    db: AsyncSession, user: User, user_repository: UserRepositoryImpl
) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    midnight_today = datetime.combine(now.date(), time.min)
    if user.last_energy_reset < midnight_today:
        user.restore_energy(restored_at=now, max_energy=settings.daily_energy)
        await user_repository.save(user)
        await db.commit()


async def _get_gene_of_day_entity(db: AsyncSession, redis: aioredis.Redis):
    gene_repository = GeneRepositoryImpl(db)
    cache_key = _gene_of_day_key()
    cached_id = await redis.get(cache_key)

    if cached_id:
        try:
            cached_gene = await gene_repository.get_by_id(UUID(cached_id))
        except ValueError:
            cached_gene = None
        if cached_gene and cached_gene.is_active:
            return cached_gene
        await redis.delete(cache_key)

    genes = await gene_repository.get_active_genes()
    if not genes:
        raise ValueError("В базе нет активных генов")

    gene = random.choice(genes)
    await redis.set(cache_key, str(gene.id), ex=get_seconds_until_midnight())
    return gene


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> BotUser | None:
    """Load bot user by Telegram ID."""
    user = await UserRepositoryImpl(db).get_by_telegram_id(TelegramId(telegram_id))
    return _to_bot_user(user)


async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
) -> BotUser:
    """Get or create a user and map it into bot context."""
    handler = GetOrCreateUserHandler(UserRepositoryImpl(db), settings.daily_energy)
    user = await handler(
        GetOrCreateUserCommand(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )
    )
    await db.commit()
    return BotUser(
        id=user.user_id,
        telegram_id=user.telegram_id,
        username=user.username,
        full_name=user.full_name,
        total_points=user.total_points,
    )


async def get_user_energy(
    db: AsyncSession, redis: aioredis.Redis, user_id: UUID | str
) -> int:
    """Return current user energy."""
    user_uuid = _parse_uuid(user_id)
    cached = await redis.get(_energy_cache_key(user_uuid))
    if cached is not None:
        return int(cached)

    user_repository = UserRepositoryImpl(db)
    user = await user_repository.get_by_id(user_uuid)
    if user is None:
        return 0

    await _restore_energy_if_needed(db, user, user_repository)
    await redis.set(
        _energy_cache_key(user_uuid), user.energy.value, ex=_ENERGY_CACHE_TTL
    )
    return user.energy.value


async def spend_energy(
    db: AsyncSession,
    redis: aioredis.Redis,
    user_id: UUID | str,
    amount: int,
) -> bool:
    """Spend a user energy amount."""
    user_uuid = _parse_uuid(user_id)
    user_repository = UserRepositoryImpl(db)
    user = await user_repository.get_by_id(user_uuid)
    if user is None:
        return False

    await _restore_energy_if_needed(db, user, user_repository)
    try:
        user.use_energy(amount)
    except ValueError:
        return False

    await user_repository.save(user)
    await db.commit()
    await redis.set(
        _energy_cache_key(user_uuid), user.energy.value, ex=_ENERGY_CACHE_TTL
    )
    return True


async def restore_daily_energy(
    db: AsyncSession, redis: aioredis.Redis, user_id: UUID | str
) -> None:
    """Restore daily energy for the user."""
    user_uuid = _parse_uuid(user_id)
    user_repository = UserRepositoryImpl(db)
    user = await user_repository.get_by_id(user_uuid)
    if user is None:
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.restore_energy(restored_at=now, max_energy=settings.daily_energy)
    await user_repository.save(user)
    await db.commit()
    await redis.set(
        _energy_cache_key(user_uuid), user.energy.value, ex=_ENERGY_CACHE_TTL
    )


async def get_gene_of_day(db: AsyncSession, redis: aioredis.Redis) -> BotGene:
    """Return the current gene of the day."""
    gene = await _get_gene_of_day_entity(db, redis)
    return BotGene(
        id=gene.id.hex,
        name=gene.name.value,
        description=gene.description,
        hint=gene.hint,
        difficulty=gene.difficulty.level,
        is_active=gene.is_active,
    )


async def invalidate_gene_of_day(db: AsyncSession, redis: aioredis.Redis) -> None:
    """Invalidate the current cached gene of the day."""
    del db
    await redis.delete(_gene_of_day_key())


async def show_daily_hint(
    db: AsyncSession, redis: aioredis.Redis, user_id: UUID | str
) -> dict[str, Any]:
    """Return the daily hint payload."""
    user_uuid = _parse_uuid(user_id)
    gene = await _get_gene_of_day_entity(db, redis)
    hints_used_raw = await redis.get(_daily_hint_key(user_uuid))
    hints_used = int(hints_used_raw) if hints_used_raw else 0

    finished_game_repository = GameRepositoryImpl(db)
    has_finished_today = (
        await finished_game_repository.has_finished_game_for_user_on_date(
            user_uuid,
            gene.name.value,
            get_today_date(),
        )
    )
    if has_finished_today:
        finished_game = (
            await finished_game_repository.get_latest_finished_by_user_and_word(
                user_uuid,
                gene.name.value,
            )
        )
        outcome = (
            "угадали слово"
            if finished_game and finished_game.is_won
            else "исчерпали все попытки"
        )
        return {
            "success": False,
            "error": "game_finished",
            "message": (
                "🔒 <b>Подсказки недоступны</b>\n\n"
                f"Вы уже завершили сегодняшнюю игру — вы {outcome}.\n"
                "Новая игра и подсказки будут доступны завтра в 00:00 🌙"
            ),
        }

    if hints_used >= 2:
        return {
            "success": False,
            "error": "daily_limit",
            "message": (
                "💡 <b>Подсказки дня исчерпаны</b>\n\n"
                "Вы уже использовали обе подсказки на сегодня.\n"
                "Новые подсказки будут доступны завтра в 00:00"
            ),
        }

    await redis.set(
        _daily_hint_key(user_uuid), hints_used + 1, ex=get_seconds_until_midnight()
    )
    difficulty = _DIFFICULTY_EMOJI.get(gene.difficulty.level, gene.difficulty.level)

    if hints_used == 0:
        return {
            "success": True,
            "hint_number": 1,
            "text": (
                "💡 <b>Подсказка дня (1/2)</b>\n\n"
                f"<b>Длина слова:</b> {len(gene.name.value)} букв(ы)\n"
                f"<b>Сложность:</b> {difficulty}\n\n"
                "💡 <i>Осталась ещё 1 подсказка</i>"
            ),
        }

    return {
        "success": True,
        "hint_number": 2,
        "text": (
            "💡 <b>Подсказка дня (2/2)</b>\n\n"
            f"<b>Длина слова:</b> {len(gene.name.value)} букв(ы)\n"
            f"<b>Сложность:</b> {difficulty}\n\n"
            f"<b>Что он делает:</b>\n{gene.hint}\n\n"
            "💪 Используйте эту информацию в игре!\n\n"
            "⚠️ <i>Это была последняя подсказка на сегодня</i>"
        ),
    }


async def reset_user_daily_state(
    db: AsyncSession, redis: aioredis.Redis, user_id: UUID | str
) -> None:
    """Remove daily state used by the dev reset command."""
    user_uuid = _parse_uuid(user_id)
    await invalidate_gene_of_day(db, redis)
    await redis.delete(_daily_hint_key(user_uuid), _energy_cache_key(user_uuid))

    game_repository = GameRepositoryImpl(db)
    achievement_repository = UserAchievementRepositoryImpl(db)
    user_prize_repository = UserPrizeRepositoryImpl(db)
    user_repository = UserRepositoryImpl(db)

    await game_repository.delete_by_user(user_uuid)
    await achievement_repository.delete_by_user(user_uuid)
    await user_prize_repository.delete_by_user(user_uuid)

    user = await user_repository.get_by_id(user_uuid)
    if user is not None:
        user.reset_points()
        await user_repository.save(user)

    await db.commit()
    await restore_daily_energy(db, redis, user_uuid)


async def close_stale_games(db: AsyncSession, user_id: UUID | str, today: date) -> None:
    """Mark active games from previous days as finished."""
    user_uuid = _parse_uuid(user_id)
    game_repository = GameRepositoryImpl(db)
    game = await game_repository.get_active_by_user(user_uuid)
    if game is None or game.created_at.date() == today:
        return

    game.surrender(finished_at=datetime.now(timezone.utc).replace(tzinfo=None))
    await game_repository.save(game)
    await db.commit()


async def find_active_game_for_gene(
    db: AsyncSession,
    user_id: UUID | str,
    gene_id: str,
) -> BotGameSession | None:
    """Find the active game for a user and gene."""
    user_uuid = _parse_uuid(user_id)
    gene_repository = GeneRepositoryImpl(db)
    gene = await gene_repository.get_by_id(_parse_uuid(gene_id))
    if gene is None:
        return None

    game = await GameRepositoryImpl(db).get_active_by_user(user_uuid)
    if game is None or game.target_word.value != gene.name.value:
        return None

    bot_gene = BotGene(
        id=gene.id.hex,
        name=gene.name.value,
        description=gene.description,
        hint=gene.hint,
        difficulty=gene.difficulty.level,
        is_active=gene.is_active,
    )
    return await _game_to_bot_session(game, gene_repository, resolved_gene=bot_gene)


async def find_finished_game_for_gene(
    db: AsyncSession,
    user_id: UUID | str,
    gene_id: str,
) -> BotGameSession | None:
    """Find the finished game for a user and gene."""
    user_uuid = _parse_uuid(user_id)
    gene_repository = GeneRepositoryImpl(db)
    game_repository = GameRepositoryImpl(db)
    gene = await gene_repository.get_by_id(_parse_uuid(gene_id))
    if gene is None:
        return None

    game = await game_repository.get_latest_finished_by_user_and_word(
        user_uuid,
        gene.name.value,
    )
    if game is None:
        return None

    bot_gene = BotGene(
        id=gene.id.hex,
        name=gene.name.value,
        description=gene.description,
        hint=gene.hint,
        difficulty=gene.difficulty.level,
        is_active=gene.is_active,
    )
    return await _game_to_bot_session(game, gene_repository, resolved_gene=bot_gene)


async def start_game_session(
    db: AsyncSession, user_id: UUID | str, gene_id: str
) -> BotGameSession:
    """Start a game session and return a bot view."""
    user_uuid = _parse_uuid(user_id)
    gene_uuid = _parse_uuid(gene_id)
    game_repository = GameRepositoryImpl(db)
    gene_repository = GeneRepositoryImpl(db)
    output = await StartGameHandler(game_repository, gene_repository)(
        StartGameCommand(user_id=user_uuid, gene_id=gene_uuid)
    )
    await db.commit()

    game = await game_repository.get_by_id(output.id)
    if game is None:
        raise ValueError("Игровая сессия не найдена")
    return await _game_to_bot_session(game, gene_repository)


async def make_attempt(
    db: AsyncSession, session_id: str, guess: str
) -> BotAttemptResult:
    """Execute one guess attempt."""
    try:
        result = await SubmitGuessHandler(
            GameRepositoryImpl(db), UserRepositoryImpl(db)
        )(SubmitGuessCommand(game_id=_parse_uuid(session_id), guess=guess))
    except Exception as error:
        raise ValueError(str(error)) from error

    await db.commit()
    return _submit_guess_output_to_bot_result(result)


async def get_game_session(db: AsyncSession, session_id: str) -> BotGameSession | None:
    """Load one game session by ID."""
    game_repository = GameRepositoryImpl(db)
    game = await game_repository.get_by_id(_parse_uuid(session_id))
    if game is None:
        return None
    return await _game_to_bot_session(game, GeneRepositoryImpl(db))


async def mark_game_hint_used(
    db: AsyncSession, session_id: str
) -> BotGameSession | None:
    """Mark the game hint as used."""
    game_repository = GameRepositoryImpl(db)
    game = await game_repository.get_by_id(_parse_uuid(session_id))
    if game is None:
        return None

    game.use_hint()
    await game_repository.save(game)
    await db.commit()
    return await _game_to_bot_session(game, GeneRepositoryImpl(db))


async def surrender_game_session(
    db: AsyncSession, session_id: str
) -> BotGameSession | None:
    """Finish a game as surrendered."""
    game_repository = GameRepositoryImpl(db)
    game = await game_repository.get_by_id(_parse_uuid(session_id))
    if game is None:
        return None

    game.surrender(finished_at=datetime.now(timezone.utc).replace(tzinfo=None))
    await game_repository.save(game)
    await db.commit()
    return await _game_to_bot_session(game, GeneRepositoryImpl(db))


async def cancel_active_game_for_user(db: AsyncSession, user_id: UUID | str) -> bool:
    """Cancel one active game for the user if it exists."""
    game_repository = GameRepositoryImpl(db)
    game = await game_repository.get_active_by_user(_parse_uuid(user_id))
    if game is None:
        return False

    game.surrender(finished_at=datetime.now(timezone.utc).replace(tzinfo=None))
    await game_repository.save(game)
    await db.commit()
    return True


async def get_user_stats(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Return user game stats."""
    query = GetUserStatsQuery(telegram_id=user_id)
    stats = await GetUserStatsHandler(StatsRepositoryImpl(db))(query)
    return _user_stats_output_to_dict(stats)


async def get_global_stats(db: AsyncSession) -> dict[str, Any]:
    """Return global admin stats."""
    stats = await GetGlobalStatsHandler(StatsRepositoryImpl(db))(GetGlobalStatsQuery())
    return _global_stats_output_to_dict(stats)


async def answer_genetics_question(
    db: AsyncSession,
    user_id: UUID | str,
    question: str,
    history: list[dict[str, str]],
) -> str:
    """Ask the llm client a genetics question."""
    service = ProxyApiLLMService(settings, LLMLogRepositoryImpl(db))
    result = await AskGeneticsQuestionHandler(service)(
        AskGeneticsQuestionCommand(
            question=question,
            history=[
                ChatHistoryItem(role=item["role"], text=item["text"])
                for item in history
                if item.get("role") in {"user", "assistant"} and item.get("text")
            ],
            user_id=_parse_uuid(user_id),
        )
    )
    await db.commit()
    return result.answer


async def get_gene_fact(
    db: AsyncSession, user_id: UUID | None, gene_name: str, gene_description: str
) -> str:
    """Ask the llm client for a gene fact."""
    service = ProxyApiLLMService(settings, LLMLogRepositoryImpl(db))
    result = await GenerateGeneFactHandler(service)(
        GenerateGeneFactCommand(
            gene_name=gene_name,
            gene_description=gene_description,
            user_id=user_id,
        )
    )
    await db.commit()
    return result.fact


async def list_genes(db: AsyncSession) -> list[BotGene]:
    """List genes for admin views."""
    genes = await ListGenesHandler(GeneRepositoryImpl(db))(ListGenesQuery())
    return [_gene_output_to_bot_gene(item) for item in genes]


async def get_gene(db: AsyncSession, gene_id: str) -> BotGene | None:
    """Load one gene by ID."""
    try:
        gene = await GetGeneByIdHandler(GeneRepositoryImpl(db))(
            GetGeneByIdQuery(gene_id=_parse_uuid(gene_id))
        )
    except Exception:
        return None
    return _gene_output_to_bot_gene(gene)


async def gene_exists(db: AsyncSession, name: str) -> bool:
    """Check whether a gene already exists by name."""
    return await GeneRepositoryImpl(db).get_by_name(name) is not None


async def create_gene(
    db: AsyncSession,
    name: str,
    description: str,
    hint: str,
    difficulty: str,
) -> BotGene:
    """Create a new gene through the current schema."""
    gene = await CreateGeneHandler(GeneRepositoryImpl(db))(
        CreateGeneCommand(
            name=name,
            description=description,
            hint=hint,
            difficulty=difficulty,
            is_active=True,
        )
    )
    await db.commit()
    return _gene_output_to_bot_gene(gene)


async def update_gene_field(
    db: AsyncSession, gene_id: str, field: str, value: str
) -> BotGene | None:
    """Update one editable gene field."""
    try:
        gene_uuid = _parse_uuid(gene_id)
        if field == "description":
            command = UpdateGeneCommand(gene_id=gene_uuid, description=value)
        elif field == "hint":
            command = UpdateGeneCommand(gene_id=gene_uuid, hint=value)
        elif field == "difficulty":
            command = UpdateGeneCommand(gene_id=gene_uuid, difficulty=value)
        else:
            return None

        gene = await UpdateGeneHandler(GeneRepositoryImpl(db))(command)
    except Exception:
        return None
    await db.commit()
    return _gene_output_to_bot_gene(gene)


async def toggle_gene_active(db: AsyncSession, gene_id: str) -> BotGene | None:
    """Toggle the gene active flag."""
    existing_gene = await get_gene(db, gene_id)
    if existing_gene is None:
        return None

    gene_uuid = _parse_uuid(gene_id)
    if existing_gene.is_active:
        gene = await DeactivateGeneHandler(GeneRepositoryImpl(db))(
            DeactivateGeneCommand(gene_id=gene_uuid)
        )
    else:
        gene = await ActivateGeneHandler(GeneRepositoryImpl(db))(
            ActivateGeneCommand(gene_id=gene_uuid)
        )
    await db.commit()
    return _gene_output_to_bot_gene(gene)


async def list_prizes(db: AsyncSession) -> list[BotPrize]:
    """List prizes for admin views."""
    prizes = await PrizeRepositoryImpl(db).get_all_prizes()
    return [_prize_to_bot(item) for item in prizes]


async def get_prize(db: AsyncSession, prize_id: str) -> BotPrize | None:
    """Load one prize by ID."""
    try:
        prize = await PrizeRepositoryImpl(db).get_by_id(_parse_uuid(prize_id))
    except ValueError:
        return None
    return _prize_to_bot(prize) if prize is not None else None


async def toggle_prize_active(db: AsyncSession, prize_id: str) -> BotPrize | None:
    """Toggle the prize active flag."""
    prize_repository = PrizeRepositoryImpl(db)
    try:
        prize = await prize_repository.get_by_id(_parse_uuid(prize_id))
    except ValueError:
        return None
    if prize is None:
        return None

    if prize.is_active:
        prize.deactivate()
    else:
        prize.activate()
    await prize_repository.save(prize)
    await db.commit()
    return _prize_to_bot(prize)


async def update_prize_field(
    db: AsyncSession, prize_id: str, field: str, value: str
) -> BotPrize | None:
    """Update one editable prize field."""
    prize_repository = PrizeRepositoryImpl(db)
    try:
        prize = await prize_repository.get_by_id(_parse_uuid(prize_id))
    except ValueError:
        return None
    if prize is None:
        return None

    if field == "description":
        prize.update_details(description=value)
    elif field == "prize_value":
        prize.update_details(value=PrizeValue(value))
    else:
        return None

    await prize_repository.save(prize)
    await db.commit()
    return _prize_to_bot(prize)


def _global_stats_output_to_dict(stats: GlobalStatsOutput) -> dict[str, Any]:
    return {
        "total_users": stats.total_users,
        "total_games": stats.total_games,
        "won_games": stats.won_games,
        "lost_games": stats.lost_games,
        "win_rate": stats.win_rate,
        "total_genes": stats.total_genes,
        "active_genes": stats.active_genes,
        "top_players": [
            {
                "telegram_id": player.telegram_id,
                "name": player.name,
                "points": player.points,
            }
            for player in stats.top_players
        ],
    }


def _user_stats_output_to_dict(stats: UserStatsOutput) -> dict[str, Any]:
    return {
        "telegram_id": stats.telegram_id,
        "username": stats.username,
        "full_name": stats.full_name,
        "total_points": stats.total_points,
        "energy": stats.energy,
        "total_games": stats.game_stats.total_games,
        "won_games": stats.game_stats.won_games,
        "lost_games": stats.game_stats.lost_games,
        "win_rate": stats.game_stats.win_rate,
    }
