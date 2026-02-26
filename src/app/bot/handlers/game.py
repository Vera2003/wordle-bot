"""
Хендлеры игрового процесса.
"""
import re
from datetime import datetime

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from ...core.config import settings
from ...db.models.game import GameSession
from ...db.models.user import User
from ...services.energy_service import EnergyService
from ...services.game_service import GameService
from ...services.gene_of_day_service import GeneOfDayService
from ...utils.time_helpers import get_today_date

router = Router()
logger = structlog.get_logger(__name__)

# Тексты кнопок главного меню — фильтруем их в игровом состоянии
MENU_TEXTS = frozenset({
    "🏠 Главное меню",
    "📊 Статистика",
    "🏆 Мои достижения",
    "📋 Правила игры",
    "💡 Подсказка дня",
    "⚡ Энергия",
    "🎮 Играть",
})


@router.message(F.text == "🎮 Играть")
async def start_game(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    redis,
    user: User | None,
):
    if not user:
        await message.answer("❌ Используйте /start")
        return

    logger.info("🎮 Start game requested", user_id=user.id)

    game_service = GameService(db)
    energy_service = EnergyService(db, redis)
    gene_of_day_service = GeneOfDayService(db, redis)

    # Закрываем устаревшие игры (начатые не сегодня)
    today = get_today_date()
    old_result = await db.execute(
        select(GameSession).where(
            GameSession.user_id == user.id,
            GameSession.is_finished == False,
        )
    )
    stale_games = old_result.scalars().all()
    for game in stale_games:
        if game.started_at.date() != today:
            game.is_finished = True
            game.finished_at = datetime.utcnow()
            logger.info("🗑️ Closed stale game", game_id=game.id)
    if stale_games:
        await db.commit()

    # Получаем ген дня
    try:
        gene = await gene_of_day_service.get()
    except ValueError:
        await message.answer("❌ Нет доступных генов для игры")
        return

    # Ищем активную игру на этот ген
    active_result = await db.execute(
        select(GameSession).where(
            GameSession.user_id == user.id,
            GameSession.gene_id == gene.id,
            GameSession.is_finished == False,
        )
    )
    existing_game = active_result.scalar_one_or_none()

    # Проверяем — может уже сыграл сегодня
    finished_result = await db.execute(
        select(GameSession).where(
            GameSession.user_id == user.id,
            GameSession.gene_id == gene.id,
            GameSession.is_finished == True,
        )
    )
    finished_game = finished_result.scalar_one_or_none()
    if finished_game:
        result_text = "победой 🎉" if finished_game.is_won else "поражением 😔"
        await message.answer(
            f"✋ Вы уже сыграли сегодня — с {result_text}\n\n"
            f"Слово было: <b>{gene.name}</b>\n\n"
            f"Новая игра будет доступна завтра в 00:00 🌙",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    current_energy = await energy_service.get_user_energy(user.id)

    if existing_game:
        logger.info("▶️ Continuing existing game", game_id=existing_game.id)
        await state.set_state(GameStates.waiting_for_guess)
        await state.update_data(session_id=existing_game.id)

        can_use_hint = current_energy >= settings.energy_per_hint and not existing_game.hint_used
        await message.answer(
            f"🎮 <b>Продолжаем игру!</b>\n\n"
            f"Слово из {len(gene.name)} букв\n"
            f"Попыток использовано: {existing_game.attempts}/{existing_game.max_attempts}\n"
            f"Энергия: {current_energy}⚡\n\n"
            f"Введите ваш вариант:",
            reply_markup=get_game_keyboard(
                has_energy=current_energy > 0, can_use_hint=can_use_hint
            ),
        )
    else:
        logger.info("🆕 Creating new game", gene_id=gene.id, gene_name=gene.name)
        session = await game_service.start_game(user.id, gene.id)
        await db.refresh(session, ["gene"])

        await state.update_data(session_id=session.id)
        await state.set_state(GameStates.waiting_for_guess)

        can_use_hint = current_energy >= settings.energy_per_hint
        hidden_word = "_ " * len(gene.name)

        await message.answer(
            GAME_START_MESSAGE.format(
                length=len(gene.name),
                hidden=hidden_word.strip(),
                attempts=session.max_attempts,
                energy=current_energy,
            ),
            reply_markup=get_game_keyboard(
                has_energy=current_energy > 0, can_use_hint=can_use_hint
            ),
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
    user: User | None,
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

    game_service = GameService(db)
    energy_service = EnergyService(db, redis)

    try:
        result = await game_service.make_attempt(session_id, guess)
        current_energy = await energy_service.get_user_energy(user.id)

        session = await db.get(GameSession, session_id)
        if not session:
            await message.answer("❌ Игровая сессия не найдена")
            await state.clear()
            return
        await db.refresh(session, ["gene"])
        result_viz = format_attempt_result(result.result)

        if result.is_correct:
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
            await state.clear()

        elif result.is_game_over:
            await message.answer(
                LOSE_MESSAGE.format(
                    word=session.gene.name,
                    gene_name=session.gene.name,
                    gene_description=session.gene.description,
                    total_points=user.total_points,
                )
            )
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

            await energy_service.spend_energy(user.id, settings.energy_per_attempt)
            current_energy -= settings.energy_per_attempt
            can_use_hint = current_energy >= settings.energy_per_hint

            await message.answer(
                ATTEMPT_RESULT_MESSAGE.format(
                    attempt_num=result.attempt_number,
                    max_attempts=session.max_attempts,
                    guess=result.guess,
                    result_visualization=result_viz,
                    attempts_left=result.attempts_left,
                    energy=current_energy,
                ),
                reply_markup=get_game_keyboard(
                    has_energy=current_energy > 0, can_use_hint=can_use_hint
                ),
            )

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.callback_query(F.data == "game:use_hint")
async def use_hint(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    redis,
    user: User | None,
):
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    session = await db.get(GameSession, session_id)
    if not session:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    await db.refresh(session, ["gene"])

    if session.hint_used:
        await callback.answer("❌ Подсказка уже использована в этой игре!", show_alert=True)
        return

    energy_service = EnergyService(db, redis)
    current_energy = await energy_service.get_user_energy(user.id)

    if current_energy < settings.energy_per_hint:
        await callback.answer(
            f"❌ Недостаточно энергии! Нужно {settings.energy_per_hint}⚡, у вас {current_energy}⚡",
            show_alert=True,
        )
        return

    await energy_service.spend_energy(user.id, settings.energy_per_hint)
    current_energy -= settings.energy_per_hint

    session.hint_used = True
    await db.commit()

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
    user: User | None,
):
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    session = await db.get(GameSession, session_id)
    if not session:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return

    session.is_finished = True
    session.finished_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session, ["gene"])

    lose_text = LOSE_MESSAGE.format(
        word=session.gene.name,
        gene_name=session.gene.name,
        gene_description=session.gene.description,
        total_points=user.total_points if user else 0,
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(lose_text)
    else:
        await callback.bot.send_message(  # type: ignore[union-attr]
            chat_id=callback.from_user.id, text=lose_text
        )
    await state.clear()
    await callback.answer("Игра завершена")