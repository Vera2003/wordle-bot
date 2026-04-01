"""
Хендлеры игрового процесса.
"""
import re
from datetime import date

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.bot.legacy_facade import (
    BotAttemptResult,
    BotGameSession,
    BotUser,
    close_stale_games,
    find_active_game_for_gene,
    find_finished_game_for_gene,
    get_game_session,
    get_gene_fact,
    get_gene_of_day,
    get_user_energy,
    make_attempt,
    mark_game_hint_used,
    spend_energy,
    start_game_session,
    surrender_game_session,
)
from ..keyboards.menu import get_game_keyboard, get_main_menu_keyboard
from ..states.game import GameStates
from ..texts.messages import (
    ATTEMPT_RESULT_MESSAGE,
    GAME_START_MESSAGE,
    LOSE_MESSAGE,
    NO_ENERGY_MESSAGE,
    WIN_MESSAGE,
    format_attempt_result,
)
from src.core.config import get_settings
from src.utils.time_helpers import get_today_date

router = Router()
logger = structlog.get_logger(__name__)
settings = get_settings()

MENU_TEXTS = frozenset({
    "🏠 Главное меню",
    "📊 Статистика",
    "🏆 Мои достижения",
    "📋 Правила игры",
    "💡 Подсказка дня",
    "⚡ Энергия",
    "🎮 Играть",
    "🤖 Спросить ИИ",  # ← ДОБАВЛЕНО чтобы не перехватывался в игре
})


# ---------------------------------------------------------------------------
# Вспомогательные функции для отправки результата игры + факта от ИИ
# ---------------------------------------------------------------------------

async def _send_win(
    message: Message,
    session: BotGameSession,
    result: BotAttemptResult,
    user: BotUser,
    db: AsyncSession,
) -> None:
    """Отправить сообщение о победе, затем интересный факт от LLM."""
    await message.answer(
        WIN_MESSAGE.format(
            word=session.gene.name,
            attempts=result.attempt_number,
            max_attempts=session.max_attempts,
            points=result.points_earned,
            gene_name=session.gene.name,
            gene_description=session.gene.description,
            total_points=user.total_points,
        )
    )
    await _send_gene_fact(message, session.gene.name, session.gene.description, db=db, user=user)


async def _send_lose(
    message: Message,
    session: BotGameSession,
    user: BotUser | None,
    db: AsyncSession,
) -> None:
    """Отправить сообщение о поражении, затем интересный факт от LLM."""
    await message.answer(
        LOSE_MESSAGE.format(
            word=session.gene.name,
            gene_name=session.gene.name,
            gene_description=session.gene.description,
            total_points=user.total_points if user else 0,
        )
    )
    await _send_gene_fact(message, session.gene.name, session.gene.description, db=db, user=user)


async def _send_gene_fact(
    message: Message,
    gene_name: str,
    gene_description: str,
    db: AsyncSession,
    user: BotUser | None,
) -> None:
    """
    Запросить интересный факт у LLM и отправить пользователю.

    Если LLM не настроена или вернула ошибку — молча пропускаем,
    игровой процесс не ломается.
    """
    if not settings.llm_enabled:
        return

    try:
        await message.bot.send_chat_action(  # type: ignore[union-attr]
            chat_id=message.chat.id, action="typing"
        )
        fact = await get_gene_fact(db, user.id if user else None, gene_name, gene_description)
        await message.answer(
            f"🧬 <b>Интересный факт о {gene_name}</b>\n\n{fact}"
        )
    except Exception as e:
        logger.warning("Failed to send gene fact", gene=gene_name, error=str(e))


# ---------------------------------------------------------------------------
# Хендлеры
# ---------------------------------------------------------------------------

@router.message(F.text == "🎮 Играть")
async def start_game(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    redis,
    user: BotUser | None = None,
):
    if not user:
        await message.answer("❌ Используйте /start")
        return

    logger.info("🎮 Start game requested", user_id=user.id)

    today = get_today_date()
    await close_stale_games(db, user.id, today)

    # Получаем ген дня
    try:
        gene = await get_gene_of_day(db, redis)
    except ValueError:
        await message.answer("❌ Нет доступных генов для игры")
        return

    existing_game = await find_active_game_for_gene(db, user.id, gene.id)
    finished_game = await find_finished_game_for_gene(db, user.id, gene.id)
    if finished_game:
        result_text = "победой 🎉" if finished_game.is_won else "поражением 😔"
        await message.answer(
            f"✋ Вы уже сыграли сегодня — с {result_text}\n\n"
            f"Слово было: <b>{gene.name}</b>\n\n"
            f"Новая игра будет доступна завтра в 00:00 🌙",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    current_energy = await get_user_energy(db, redis, user.id)

    if existing_game:
        logger.info("▶️ Continuing existing game", game_id=existing_game.id)
        await state.set_state(GameStates.waiting_for_guess)
        await state.update_data(session_id=existing_game.id)

        await message.answer(
            f"🎮 <b>Продолжаем игру!</b>\n\n"
            f"Слово из {len(gene.name)} букв\n"
            f"Попыток использовано: {existing_game.attempts}/{existing_game.max_attempts}\n"
            f"Энергия: {current_energy}⚡\n\n"
            f"Введите ваш вариант:",
            reply_markup=get_game_keyboard(),
        )
    else:
        logger.info("🆕 Creating new game", gene_id=gene.id, gene_name=gene.name)
        session = await start_game_session(db, user.id, gene.id)

        await state.update_data(session_id=session.id)
        await state.set_state(GameStates.waiting_for_guess)

        hidden_word = "_ " * len(gene.name)
        await message.answer(
            GAME_START_MESSAGE.format(
                length=len(gene.name),
                hidden=hidden_word.strip(),
                attempts=session.max_attempts,
                energy=current_energy,
            ),
            reply_markup=get_game_keyboard(),
        )


@router.message(
    GameStates.waiting_for_guess,
    F.text,
    ~F.text.in_(MENU_TEXTS),
)
async def process_guess(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    redis,
    user: BotUser | None = None,
):
    if not user:
        await message.answer("❌ Используйте /start")
        await state.clear()
        return

    logger.info("🎯 Guess received", user_id=user.id, guess=message.text)

    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        logger.error("❌ No session_id in FSM state")
        await message.answer("❌ Игра не найдена. Начните новую.")
        await state.clear()
        return

    if not message.text:
        return

    guess = message.text.strip().upper()
    if not re.match(r"^[A-Z0-9]+$", guess):
        await message.answer("❌ Используйте только латинские буквы и цифры!")
        return

    try:
        result = await make_attempt(db, session_id, guess)
        current_energy = await get_user_energy(db, redis, user.id)

        session = await get_game_session(db, session_id)
        if not session:
            await message.answer("❌ Игровая сессия не найдена")
            await state.clear()
            return
        result_viz = format_attempt_result(result.result)

        if result.is_correct:
            # ↓↓↓ ИЗМЕНЕНО: вместо прямого message.answer — вызов _send_win
            await _send_win(message, session, result, user, db=db)
            await state.clear()

        elif result.is_game_over:
            # ↓↓↓ ИЗМЕНЕНО: вместо прямого message.answer — вызов _send_lose
            await _send_lose(message, session, user, db=db)
            await state.clear()

        else:
            if current_energy < settings.energy_per_attempt:
                await message.answer(
                    ATTEMPT_RESULT_MESSAGE.format(
                        attempt_num=result.attempt_number,
                        max_attempts=session.max_attempts,
                        guess=result.guess,
                        result_visualization=result_viz,
                        attempts_left=result.attempts_left,
                        energy=current_energy,
                    )
                    + f"\n\n{NO_ENERGY_MESSAGE.format(current_energy=current_energy, required_energy=settings.energy_per_attempt)}",
                    reply_markup=get_main_menu_keyboard(),
                )
                await state.clear()
                return

            await spend_energy(db, redis, user.id, settings.energy_per_attempt)
            current_energy -= settings.energy_per_attempt

            await message.answer(
                ATTEMPT_RESULT_MESSAGE.format(
                    attempt_num=result.attempt_number,
                    max_attempts=session.max_attempts,
                    guess=result.guess,
                    result_visualization=result_viz,
                    attempts_left=result.attempts_left,
                    energy=current_energy,
                ),
                reply_markup=get_game_keyboard(),
            )

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.callback_query(F.data == "game:use_hint")
async def use_hint(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    redis,
    user: BotUser | None = None,
):
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    session = await get_game_session(db, session_id)
    if not session:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    if session.hint_used:
        await callback.answer("❌ Подсказка уже использована в этой игре!", show_alert=True)
        return

    current_energy = await get_user_energy(db, redis, user.id)

    if current_energy < settings.energy_per_hint:
        await callback.answer(
            f"❌ Недостаточно энергии! Нужно {settings.energy_per_hint}⚡, у вас {current_energy}⚡",
            show_alert=True,
        )
        return

    await spend_energy(db, redis, user.id, settings.energy_per_hint)
    current_energy -= settings.energy_per_hint

    session = await mark_game_hint_used(db, session.id)
    if session is None:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            f"💡 <b>Подсказка о гене</b>\n\n"
            f"{session.gene.hint}\n\n"
            f"Энергия: {current_energy}⚡ (-{settings.energy_per_hint}⚡)"
        )
    await callback.answer("💡 Подсказка использована!")


@router.callback_query(F.data == "game:surrender")
async def surrender_game(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: BotUser | None = None,
):
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    session = await surrender_game_session(db, session_id)
    if not session:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    if isinstance(callback.message, Message):
        await _send_lose(callback.message, session, user, db=db)

    await state.clear()
    await callback.answer("Игра завершена")