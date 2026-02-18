from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import re
from datetime import datetime, timedelta
import random

from ..keyboards.menu import get_main_menu_keyboard, get_game_keyboard#, get_game_finished_keyboard
from ..texts.messages import (
    GAME_START_MESSAGE, ATTEMPT_RESULT_MESSAGE, WIN_MESSAGE, LOSE_MESSAGE,
    NO_ENERGY_MESSAGE, ERROR_INVALID_WORD, ERROR_ALREADY_IN_GAME,
    HINT_MESSAGE, format_attempt_result
)
from ..states.game import GameStates
from ...db.models.user import User
from ...db.models.game import GameSession
from ...db.models.gene import Gene
from ...services.game_service import GameService
from ...services.energy_service import EnergyService
from ...services.user_service import UserService
from ...core.config import settings
from ...utils.time_helpers import get_today_date, get_seconds_until_midnight, get_today_str

router = Router()


@router.message(F.text == "🎮 Играть")
async def start_game(message: Message, state: FSMContext, db: AsyncSession, redis):
    """
    Начинает новую игру или продолжает существующую
    
    Логика:
    1. Получаем пользователя через UserService
    2. Закрываем все старые игры (не сегодняшние)
    3. Получаем/создаём ген дня из Redis
    4. Проверяем наличие активной игры на сегодня
    5. Если есть - продолжаем, если нет - создаём новую
    6. Выводим игровое сообщение с клавиатурой
    """
    logger = structlog.get_logger(__name__)
    logger.info("🎮 Start game requested", user_id=message.from_user.id)
    
    # === 1. ПОЛУЧАЕМ ПОЛЬЗОВАТЕЛЯ ===
    user_service = UserService(db)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    logger.info("👤 User found", user_id=user.id, username=user.username)
    
    # === 2. ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ ===
    game_service = GameService(db)
    energy_service = EnergyService(db, redis)
    
    # === 3. ЗАКРЫВАЕМ СТАРЫЕ ИГРЫ (НЕ СЕГОДНЯШНИЕ) ===
    today = get_today_date()
    
    old_games_query = select(GameSession).where(
        GameSession.user_id == user.id,
        GameSession.is_finished == False
    )
    result = await db.execute(old_games_query)
    old_games = result.scalars().all()
    
    logger.info("🔍 Checking old games", count=len(old_games))
    
    # Завершаем игры, которые не сегодняшние
    for game in old_games:
        if game.started_at.date() != today:
            game.is_finished = True
            game.finished_at = datetime.utcnow()
            logger.info("🗑️ Closed old game", game_id=game.id, started=game.started_at)
    
    if old_games:
        await db.commit()
    
    # === 4. ПОЛУЧАЕМ/СОЗДАЁМ ГЕН ДНЯ ===
    today_str = get_today_str()
    gene_of_day_key = f"gene_of_day:{today_str}"
    gene_id = await redis.get(gene_of_day_key)
    
    logger.info("🧬 Gene of day check", gene_id=gene_id)
    
    if gene_id:
        # Ген дня уже выбран
        gene = await db.get(Gene, int(gene_id))
        if not gene or not gene.is_active:
            # Если ген удалён/деактивирован, выбираем новый
            await redis.delete(gene_of_day_key)
            gene = None
    else:
        gene = None
    
    if not gene:
        # Выбираем случайный активный ген
        query = select(Gene).where(Gene.is_active == True)
        result = await db.execute(query)
        genes = result.scalars().all()
        
        if not genes:
            await message.answer("❌ Нет доступных генов для игры")
            return
        
        gene = random.choice(genes)
        logger.info("🎲 Random gene selected", gene_id=gene.id, gene_name=gene.name)
        
        # Сохраняем в Redis до конца дня
        ttl = get_seconds_until_midnight()
        await redis.set(gene_of_day_key, gene.id, ex=ttl)
    
    # === 5. ПРОВЕРЯЕМ НАЛИЧИЕ АКТИВНОЙ ИГРЫ НА СЕГОДНЯ ===
    active_game_query = select(GameSession).where(
        GameSession.user_id == user.id,
        GameSession.gene_id == gene.id,
        GameSession.is_finished == False
    )
    result = await db.execute(active_game_query)
    existing_game = result.scalar_one_or_none()
    
    # Получаем текущую энергию (для отображения)
    current_energy = await energy_service.get_user_energy(user.id)
    
    if existing_game:
        # === 6A. ПРОДОЛЖАЕМ СУЩЕСТВУЮЩУЮ ИГРУ ===
        logger.info("▶️ Continuing existing game", game_id=existing_game.id, attempts=existing_game.attempts)
        
        await state.set_state(GameStates.waiting_for_guess)
        await state.update_data(session_id=existing_game.id)
        
        can_use_hint = (
            current_energy >= settings.energy_per_hint 
            and not existing_game.hint_used
        )
        
        await message.answer(
            f"🎮 <b>Продолжаем игру!</b>\n\n"
            f"Слово из {len(gene.name)} букв\n"
            f"Попыток использовано: {existing_game.attempts}/{existing_game.max_attempts}\n"
            f"Энергия: {current_energy}⚡ (для подсказок)\n\n"
            f"Введите ваш вариант:",
            reply_markup=get_game_keyboard(
                has_energy=current_energy > 0,
                can_use_hint=can_use_hint
            )
        )
    else:
        # === 6B. СОЗДАЁМ НОВУЮ ИГРУ ===
        logger.info("🆕 Creating new game", gene_id=gene.id, gene_name=gene.name)
        
        session = await game_service.start_game(user.id, gene.id)
        await db.refresh(session, ['gene'])
        
        logger.info("✅ Game created", session_id=session.id)
        
        # Сохраняем session_id в FSM
        await state.update_data(session_id=session.id)
        await state.set_state(GameStates.waiting_for_guess)
        
        can_use_hint = current_energy >= settings.energy_per_hint
        hidden_word = "_ " * len(gene.name)

        text = GAME_START_MESSAGE.format(
            length=len(gene.name),
            hidden=hidden_word.strip(),
            attempts=session.max_attempts,
            energy=current_energy
        )
        
        await message.answer(
            text,
            reply_markup=get_game_keyboard(
                has_energy=current_energy > 0,
                can_use_hint=can_use_hint
            )
        )
        
        logger.info("📨 Game start message sent")


# ИСПРАВЛЕНИЕ: Исключаем кнопки меню из обработки игровых попыток
@router.message(
    GameStates.waiting_for_guess,
    F.text,
    ~F.text.in_([
        "🏠 Главное меню",
        "📊 Статистика", 
        "🏆 Мои достижения",
        "📋 Правила игры",
        "💡 Подсказка дня",
        "⚡ Энергия",
        "🎮 Играть"
    ])
)
async def process_guess(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    redis
):
    """Обрабатывает попытку угадывания"""
    logger = structlog.get_logger(__name__)
    
    logger.info("🎯 Guess received", user_id=message.from_user.id, guess=message.text)
    
    data = await state.get_data()
    session_id = data.get('session_id')
    
    logger.info("📦 FSM data", session_id=session_id, all_data=data)
    
    if not session_id:
        logger.error("❌ No session_id in FSM")
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
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
        
    # Сервисы
    game_service = GameService(db)
    energy_service = EnergyService(db, redis)
    
    try:
        # Делаем попытку
        result = await game_service.make_attempt(session_id, guess)
        
        # Получаем текущую энергию
        current_energy = await energy_service.get_user_energy(user.id)
        
        # Получаем сессию (нужна во всех ветках)
        session = await db.get(GameSession, session_id)
        await db.refresh(session, ['gene'])
        
        # Форматируем результат
        result_viz = format_attempt_result(result.result)
        
        if result.is_correct:
            # ПОБЕДА!
            # session = await db.get(GameSession, session_id)
            # await db.refresh(session, ['gene'])
            
            await message.answer(
                WIN_MESSAGE.format(
                    word=session.gene.name,
                    attempts=result.attempt_number,
                    max_attempts=session.max_attempts,
                    points=result.points_earned,
                    gene_name=session.gene.name,
                    gene_description=session.gene.description,
                    total_points=user.total_points
                )#,
                #reply_markup=get_game_finished_keyboard(is_won=True)
            )
            await state.clear()
            
        elif result.is_game_over:
            # ПРОИГРЫШ
            # session = await db.get(GameSession, session_id)
            # await db.refresh(session, ['gene'])
            
            await message.answer(
                LOSE_MESSAGE.format(
                    word=session.gene.name,
                    gene_name=session.gene.name,
                    gene_description=session.gene.description,
                    total_points=user.total_points
                )#,
                #reply_markup=get_game_finished_keyboard(is_won=False)
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
    """Использует подсказку в игре (платную, 2⚡)"""
    from ...services.hint_service import HintService
    from ...services.energy_service import EnergyService
    
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if not session_id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    
    # Получаем пользователя и сессию
    stmt = select(User).where(User.telegram_id == callback.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    session = await db.get(GameSession, session_id)
    await db.refresh(session, ['gene'])
    
    # Проверяем, использована ли уже подсказка в игре
    if session.hint_used:
        await callback.answer("❌ Подсказка уже использована в этой игре!", show_alert=True)
        return
    
    # Проверяем энергию
    energy_service = EnergyService(db, redis)
    current_energy = await energy_service.get_user_energy(user.id)
    
    if current_energy < settings.energy_per_hint:
        await callback.answer(
            f"❌ Недостаточно энергии! Нужно {settings.energy_per_hint}⚡",
            show_alert=True
        )
        return
    
    # Тратим энергию
    await energy_service.spend_energy(user.id, settings.energy_per_hint)
    current_energy -= settings.energy_per_hint
    
    # Помечаем подсказку как использованную
    session.hint_used = True
    await db.commit()
    
    # Используем единый сервис для получения подсказки
    hint_service = HintService(db, redis)
    hint_result = await hint_service.show_hint(user.id, hint_type="in_game")
    
    # Показываем hint гена (игнорируем дневной лимит для платной подсказки)
    await callback.message.answer(
        f"💡 <b>Подсказка о гене</b>\n\n"
        f"{session.gene.hint}\n\n"
        f"Энергия: {current_energy}⚡ (-{settings.energy_per_hint}⚡)"
    )
    await callback.answer("💡 Подсказка использована!")


@router.callback_query(F.data == "game:surrender")
async def surrender_game(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Сдаться в игре"""
    from datetime import datetime
    
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
    
    stmt = select(User).where(User.telegram_id == callback.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    await callback.message.edit_text(
        LOSE_MESSAGE.format(
            word=session.gene.name,
            gene_name=session.gene.name,
            gene_description=session.gene.description,
            total_points=user.total_points
        )#,
        #reply_markup=get_game_finished_keyboard(is_won=False)
    )
    
    await state.clear()
    await callback.answer("Игра завершена")