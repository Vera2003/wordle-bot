from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import re

from ..keyboards.menu import get_main_menu_keyboard
from ..keyboards.game import get_game_keyboard, get_game_finished_keyboard
from ..texts.messages import (
    GAME_START_MESSAGE, ATTEMPT_RESULT_MESSAGE, WIN_MESSAGE, LOSE_MESSAGE,
    NO_ENERGY_MESSAGE, ERROR_INVALID_WORD, ERROR_ALREADY_IN_GAME,
    HINT_MESSAGE, format_attempt_result
)
from ..states.game import GameStates
from ...db.models.user import User
from ...services.game_service import GameService
from ...services.energy_service import EnergyService
from ...core.config import settings

router = Router()


@router.message(F.text == "🎮 Играть")
@router.callback_query(F.data == "game:play_again")
async def start_game(
    event: Message | CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    redis
):
    """Начинает новую игру"""
    # Получаем user_id
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    else:
        user_id = event.from_user.id
        message = event
    
    # Получаем пользователя
    user = await db.get(User, user_id)
    if not user:
        await message.answer("❌ Используйте /start для регистрации")
        return
    
    # Проверяем энергию
    energy_service = EnergyService(db, redis)
    current_energy = await energy_service.get_user_energy(user.id)
    
    if current_energy < settings.energy_per_attempt:
        await message.answer(
            NO_ENERGY_MESSAGE.format(
                current_energy=current_energy,
                required_energy=settings.energy_per_attempt
            ),
            reply_markup=get_main_menu_keyboard()
        )
        if isinstance(event, CallbackQuery):
            await event.answer()
        return
    
    # Проверяем активную игру
    game_service = GameService(db)
    active_game = await game_service.get_active_game(user.id)
    
    if active_game:
        await message.answer(
            ERROR_ALREADY_IN_GAME,
            reply_markup=get_main_menu_keyboard()
        )
        if isinstance(event, CallbackQuery):
            await event.answer()
        return
    
    # Создаём новую игру
    session = await game_service.start_game(user.id)
    await db.refresh(session, ['gene'])
    
    # Тратим энергию на первую попытку
    await energy_service.spend_energy(user.id, settings.energy_per_attempt)
    current_energy -= settings.energy_per_attempt
    
    # Сохраняем session_id в FSM
    await state.update_data(session_id=session.id)
    await state.set_state(GameStates.waiting_for_guess)
    
    can_use_hint = current_energy >= settings.energy_per_hint
    
    text = GAME_START_MESSAGE.format(
        length=session.gene.length,
        attempts=session.max_attempts,
        energy=current_energy
    )
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=get_game_keyboard(
                has_energy=current_energy > 0,
                can_use_hint=can_use_hint
            )
        )
        await event.answer()
    else:
        await message.answer(
            text,
            reply_markup=get_game_keyboard(
                has_energy=current_energy > 0,
                can_use_hint=can_use_hint
            )
        )


@router.message(GameStates.waiting_for_guess, F.text)
async def process_guess(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    redis
):
    """Обрабатывает попытку угадывания"""
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if not session_id:
        await message.answer("❌ Игра не найдена. Начните новую игру.")
        await state.clear()
        return
    
    # Валидация ввода (только латиница и цифры)
    guess = message.text.strip().upper()
    if not re.match(r'^[A-Z0-9]+$', guess):
        await message.answer(
            "❌ Используйте только латинские буквы и цифры!"
        )
        return
    
    # Получаем user_id
    user = await db.get(User, message.from_user.id)
    
    # Сервисы
    game_service = GameService(db)
    energy_service = EnergyService(db, redis)
    
    try:
        # Делаем попытку
        result = await game_service.make_attempt(session_id, guess)
        
        # Получаем текущую энергию
        current_energy = await energy_service.get_user_energy(user.id)
        
        # Форматируем результат
        result_viz = format_attempt_result(result.result)
        
        if result.is_correct:
            # ПОБЕДА!
            session = await db.get(GameSession, session_id)
            await db.refresh(session, ['gene'])
            
            await message.answer(
                WIN_MESSAGE.format(
                    word=session.gene.name,
                    attempts=result.attempt_number,
                    max_attempts=session.max_attempts,
                    points=result.points_earned,
                    gene_name=session.gene.name,
                    gene_description=session.gene.description,
                    total_points=user.total_points
                ),
                reply_markup=get_game_finished_keyboard(is_won=True)
            )
            await state.clear()
            
        elif result.is_game_over:
            # ПРОИГРЫШ
            session = await db.get(GameSession, session_id)
            await db.refresh(session, ['gene'])
            
            await message.answer(
                LOSE_MESSAGE.format(
                    word=session.gene.name,
                    gene_name=session.gene.name,
                    gene_description=session.gene.description,
                    total_points=user.total_points
                ),
                reply_markup=get_game_finished_keyboard(is_won=False)
            )
            await state.clear()
            
        else:
            # Игра продолжается
            # Проверяем, хватает ли энергии на следующую попытку
            if current_energy < settings.energy_per_attempt:
                await message.answer(
                    ATTEMPT_RESULT_MESSAGE.format(
                        attempt_num=result.attempt_number,
                        max_attempts=session.max_attempts,
                        guess=result.guess,
                        result_visualization=result_viz,
                        attempts_left=result.attempts_left,
                        energy=current_energy
                    ) + f"\n\n{NO_ENERGY_MESSAGE.format(current_energy=current_energy, required_energy=settings.energy_per_attempt)}",
                    reply_markup=get_main_menu_keyboard()
                )
                await state.clear()
                return
            
            # Тратим энергию на следующую попытку
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
                    energy=current_energy
                ),
                reply_markup=get_game_keyboard(
                    has_energy=current_energy > 0,
                    can_use_hint=can_use_hint
                )
            )
    
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "game:use_hint")
async def use_hint(callback: CallbackQuery, state: FSMContext, db: AsyncSession, redis):
    """Использует подсказку"""
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if not session_id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    
    # Получаем пользователя и сессию
    user = await db.get(User, callback.from_user.id)
    session = await db.get(GameSession, session_id)
    await db.refresh(session, ['gene'])
    
    # Проверяем энергию
    energy_service = EnergyService(db, redis)
    current_energy = await energy_service.get_user_energy(user.id)
    
    if current_energy < settings.energy_per_hint:
        await callback.answer(
            f"❌ Недостаточно энергии! Нужно {settings.energy_per_hint}⚡",
            show_alert=True
        )
        return
    
    # Проверяем, использована ли уже подсказка
    if session.hint_used:
        await callback.answer("❌ Подсказка уже использована!", show_alert=True)
        return
    
    # Тратим энергию
    await energy_service.spend_energy(user.id, settings.energy_per_hint)
    current_energy -= settings.energy_per_hint
    
    # Помечаем подсказку как использованную
    session.hint_used = True
    await db.commit()
    
    await callback.message.answer(
        HINT_MESSAGE.format(
            hint=session.gene.hint,
            energy=current_energy
        )
    )
    await callback.answer("💡 Подсказка использована!")


@router.callback_query(F.data == "game:surrender")
async def surrender_game(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Сдаться в игре"""
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if not session_id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    
    # Завершаем игру
    session = await db.get(GameSession, session_id)
    session.is_finished = True
    session.finished_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session, ['gene'])
    
    user = await db.get(User, callback.from_user.id)
    
    await callback.message.edit_text(
        LOSE_MESSAGE.format(
            word=session.gene.name,
            gene_name=session.gene.name,
            gene_description=session.gene.description,
            total_points=user.total_points
        ),
        reply_markup=get_game_finished_keyboard(is_won=False)
    )
    
    await state.clear()
    await callback.answer("Игра завершена")
