from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import re
from datetime import datetime, timedelta

from ..keyboards.menu import get_main_menu_keyboard
from ..keyboards.game import get_game_keyboard, get_game_finished_keyboard
from ..texts.messages import (
    GAME_START_MESSAGE, ATTEMPT_RESULT_MESSAGE, WIN_MESSAGE, LOSE_MESSAGE,
    NO_ENERGY_MESSAGE, ERROR_INVALID_WORD, ERROR_ALREADY_IN_GAME,
    HINT_MESSAGE, format_attempt_result
)
from ..states.game import GameStates
from ...db.models.user import User
from ...db.models.game import GameSession
from ...services.game_service import GameService
from ...services.energy_service import EnergyService
from ...core.config import settings

router = Router()


@router.message(F.text == "🎮 Играть")
async def start_game(message: Message, state: FSMContext, db: AsyncSession, redis):
    from datetime import datetime, timedelta
    from ...db.models.game import GameSession
    from ...db.models.gene import Gene
    import random
    
    logger = structlog.get_logger(__name__)
    logger.info("🎮 Start game requested", user_id=message.from_user.id)
    
    # Получаем пользователя
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    logger.info("👤 User found", user_id=user.id, username=user.username)
    
    # Сервисы
    game_service = GameService(db)
    energy_service = EnergyService(db, redis)
    
    # Проверяем энергию
    current_energy = await energy_service.get_user_energy(user.id)
    logger.info("⚡ Energy check", energy=current_energy, required=settings.energy_per_attempt)
    
    if current_energy < settings.energy_per_attempt:
        await message.answer(
            NO_ENERGY_MESSAGE.format(
                current_energy=current_energy,
                required_energy=settings.energy_per_attempt
            ),
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # НОВОЕ: Проверяем и завершаем старые игры
    today = datetime.utcnow().date()
    
    # Находим все незавершенные игры
    old_games_query = select(GameSession).where(
        GameSession.user_id == user.id,
        GameSession.is_finished == False
    )
    result = await db.execute(old_games_query)
    old_games = result.scalars().all()
    
    logger.info("🔍 Checking old games", count=len(old_games))
    
    # Завершаем игры, которые не сегодняшние
    for game in old_games:
        if game.created_at.date() != today:
            game.is_finished = True
            game.finished_at = datetime.utcnow()
            logger.info("🗑️ Closed old game", game_id=game.id)
    
    if old_games:
        await db.commit()
    
    # Получаем ген дня из Redis
    today_str = today.strftime("%Y-%m-%d")
    gene_of_day_key = f"gene_of_day:{today_str}"
    gene_id = await redis.get(gene_of_day_key)
    
    logger.info("🧬 Gene of day check", gene_id=gene_id)
    
    if gene_id:
        gene = await db.get(Gene, int(gene_id))
    else:
        # Если нет гена дня, выбираем случайный
        query = select(Gene).where(Gene.is_active == True)
        result = await db.execute(query)
        genes = result.scalars().all()
        
        if not genes:
            await message.answer("❌ Нет доступных генов для игры")
            return
        
        gene = random.choice(genes)
        logger.info("🎲 Random gene selected", gene_id=gene.id, gene_name=gene.name)
        
        # Сохраняем в Redis до конца дня
        now = datetime.utcnow()
        midnight = datetime.combine(now.date(), datetime.min.time()) + timedelta(days=1)
        ttl = int((midnight - now).total_seconds())
        await redis.set(gene_of_day_key, gene.id, ex=ttl)
    
    # Проверяем, есть ли уже активная игра на сегодня с этим геном
    active_game_query = select(GameSession).where(
        GameSession.user_id == user.id,
        GameSession.gene_id == gene.id,
        GameSession.is_finished == False
    )
    result = await db.execute(active_game_query)
    existing_game = result.scalar_one_or_none()
    
    if existing_game:
        # Продолжаем существующую игру
        logger.info("▶️ Continuing existing game", game_id=existing_game.id, attempts=existing_game.attempts)
        
        await state.set_state(GameStates.waiting_for_guess)  # ← ИСПРАВЛЕНО!
        await state.update_data(
            session_id=existing_game.id  # ← ИСПРАВЛЕНО! было game_id
        )
        
        await message.answer(
            f"🎮 Продолжаем игру!\n\n"
            f"Слово из {len(gene.name)} букв\n"
            f"Попыток использовано: {existing_game.attempts}/6\n\n"
            f"Введите ваше слово:",
            reply_markup=get_game_keyboard()
        )
    else:
        # Создаём новую игру
        logger.info("🆕 Creating new game", gene_id=gene.id, gene_name=gene.name)
        
        session = await game_service.start_game(user.id, gene.id)
        await db.refresh(session, ['gene'])
        
        logger.info("✅ Game created", session_id=session.id)
        
        # Тратим энергию на первую попытку
        await energy_service.spend_energy(user.id, settings.energy_per_attempt)
        current_energy -= settings.energy_per_attempt
        
        logger.info("💰 Energy spent", remaining=current_energy)
        
        # Сохраняем session_id в FSM
        await state.update_data(session_id=session.id)
        await state.set_state(GameStates.waiting_for_guess)  # ← ИСПРАВЛЕНО!
        
        can_use_hint = current_energy >= settings.energy_per_hint

        hidden_word = "_" * len(gene.name)

        text = GAME_START_MESSAGE.format(
        length=len(gene.name),
        hidden=hidden_word,
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
    stmt = select(User).where(User.telegram_id == callback.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
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
        ),
        reply_markup=get_game_finished_keyboard(is_won=False)
    )
    
    await state.clear()
    await callback.answer("Игра завершена")