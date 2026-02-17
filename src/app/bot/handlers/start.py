from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import delete

from ..keyboards.menu import get_main_menu_keyboard
from ..texts.messages import WELCOME_MESSAGE, MAIN_MENU_MESSAGE, RULES_MESSAGE
from ..states.game import GameStates
from ...db.models.user import User
from ...db.models.game import GameSession
from ...db.models.achievements import UserAchievement
from ...db.models.prize import UserPrize
from ...services.energy_service import EnergyService
from ...core.config import settings

from datetime import datetime, time, timedelta

import structlog

logger = structlog.get_logger(__name__)

router = Router()

@router.message(Command("resetday"))
async def cmd_reset_day(message: Message, db: AsyncSession, redis):
    ADMIN_IDS = [1085711478]  # или settings.admin_ids
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде")
        return

    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Используйте /start")
        return

    today = datetime.utcnow().strftime("%Y-%m-%d")
    gene_of_day_key = f"gene_of_day:{today}"
    user_hints_key = f"user:{user.id}:daily_hints:{today}"

    await redis.delete(gene_of_day_key)
    await redis.delete(user_hints_key)

    # закрываем и удаляем игровые данные
    active_games_query = select(GameSession).where(
        GameSession.user_id == user.id,
        GameSession.is_finished == False
    )
    result = await db.execute(active_games_query)
    active_games = result.scalars().all()

    for game in active_games:
        game.is_finished = True
        game.finished_at = datetime.utcnow()

    await db.execute(delete(GameSession).where(GameSession.user_id == user.id))
    await db.execute(delete(UserAchievement).where(UserAchievement.user_id == user.id))
    await db.execute(delete(UserPrize).where(UserPrize.user_id == user.id))

    user.total_points = 0
    await db.commit()

    # восстановление дневной энергии
    energy_service = EnergyService(db, redis)
    await energy_service.restore_daily_energy(user.id)

    # важный шаг: сброс кэша энергии
    await redis.delete(f"user:{user.id}:energy")
    
    await message.answer(
        "✅ <b>День сброшен!</b>\n\n"
        "• Слово дня удалено\n"
        "• Счетчик подсказок обнулен\n"
        "• Активные игры завершены\n\n"
        "Теперь можете начать новую игру с новым словом!",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession):
    """Обработчик команды /start"""
    # Ищем пользователя по telegram_id
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            energy=settings.daily_energy
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    await state.set_state(GameStates.main_menu)
    
    await message.answer(
        WELCOME_MESSAGE.format(energy=settings.daily_energy),
        reply_markup=get_main_menu_keyboard()
    )


@router.message(F.text == "🏠 Главное меню")
@router.callback_query(F.data == "menu:main")
async def show_main_menu(event: Message | CallbackQuery, state: FSMContext):
    """Показывает главное меню"""
    await state.set_state(GameStates.main_menu)
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            MAIN_MENU_MESSAGE,
            reply_markup=get_main_menu_keyboard()
        )
        await event.answer()
    else:
        await event.answer(
            MAIN_MENU_MESSAGE,
            reply_markup=get_main_menu_keyboard()
        )


@router.message(F.text == "📋 Правила игры")
async def show_rules(message: Message):
    """Показывает правила игры"""
    await message.answer(
        RULES_MESSAGE.format(daily_energy=settings.daily_energy),
        reply_markup=get_main_menu_keyboard()
    )


@router.message(F.text == "💡 Подсказка дня")
async def show_daily_hint(message: Message, db: AsyncSession, redis):
    import random
    from datetime import datetime, timedelta
    from ...db.models.gene import Gene

    # Получаем пользователя
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Используйте /start")
        return

    today = datetime.utcnow().strftime("%Y-%m-%d")
    gene_of_day_key = f"gene_of_day:{today}"
    user_hints_key = f"user:{user.id}:daily_hints:{today}"

    # Счётчик подсказок
    hints_used = await redis.get(user_hints_key)
    hints_used = int(hints_used) if hints_used else 0

    if hints_used >= 2:
        await message.answer(
            "💡 <b>Подсказки дня исчерпаны</b>\n\n"
            "Вы уже использовали обе подсказки на сегодня.\n"
            "Новые подсказки будут доступны завтра в 00:00",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # TTL до полуночи (один раз)
    now = datetime.utcnow()
    midnight = datetime.combine(now.date(), datetime.min.time()) + timedelta(days=1)
    ttl = int((midnight - now).total_seconds())

    # Ген дня
    gene_id = await redis.get(gene_of_day_key)
    
    if gene_id:
        gene = await db.get(Gene, int(gene_id))
    else:
        query = select(Gene).where(Gene.is_active == True)
        result = await db.execute(query)
        genes = result.scalars().all()

        if not genes:
            await message.answer(
                "💡 Подсказки пока недоступны",
                reply_markup=get_main_menu_keyboard()
            )
            return

        gene = random.choice(genes)
        await redis.set(gene_of_day_key, gene.id, ex=ttl)

    # ТЕПЕРЬ gene точно определен - можно логировать
    logger.info(f"DEBUG: Gene of day ID={gene.id}, name='{gene.name}', length={len(gene.name)}")

    hints_used += 1

    if hints_used == 1:
        text = (
            f"💡 <b>Подсказка дня (1/2)</b>\n\n"
            f"<b>Длина слова:</b> {len(gene.name)} букв(ы)\n"
            f"<b>Сложность:</b> "
            f"{'🟢 Легкая' if gene.difficulty == 'easy' else '🟡 Средняя' if gene.difficulty == 'medium' else '🔴 Сложная'}\n\n"
            f"💡 <i>Осталась ещё 1 подсказка</i>"
        )
    else:
        text = (
            f"💡 <b>Подсказка дня (2/2)</b>\n\n"
            f"<b>Длина слова:</b> {len(gene.name)} букв(ы)\n"
            f"<b>Сложность:</b> "
            f"{'🟢 Легкая' if gene.difficulty == 'easy' else '🟡 Средняя' if gene.difficulty == 'medium' else '🔴 Сложная'}\n\n"
            f"<b>Что он делает:</b>\n{gene.hint}\n\n"
            f"💪 Используйте эту информацию в игре!\n\n"
            f"⚠️ <i>Это была последняя подсказка на сегодня</i>"
        )

    await redis.set(user_hints_key, hints_used, ex=ttl)

    await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(F.text == "⚡ Энергия")
async def show_energy(
    message: Message, 
    db: AsyncSession,
    redis
):
    """Показывает информацию об энергии"""
    from ..texts.messages import ENERGY_MESSAGE
    
    energy_service = EnergyService(db, redis)
    
    # Ищем пользователя по telegram_id
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start")
        return
    
    current_energy = await energy_service.get_user_energy(user.id)
    
    await message.answer(
        ENERGY_MESSAGE.format(
            current_energy=current_energy,
            max_energy=settings.daily_energy,
            daily_energy=settings.daily_energy
        ),
        reply_markup=get_main_menu_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь"""
    await message.answer(
        RULES_MESSAGE.format(daily_energy=settings.daily_energy),
        reply_markup=get_main_menu_keyboard()
    )


@router.message(Command("cancel"))
async def cmd_cancel_game(message: Message, state: FSMContext, db: AsyncSession):
    """Отменить текущую игру (если зависла)"""
    
    # Получаем пользователя
    stmt = select(User).where(User.telegram_id == message.from_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    # Ищем активную игру
    game_query = select(GameSession).where(
        GameSession.user_id == user.id,
        GameSession.is_finished == False
    )
    result = await db.execute(game_query)
    active_game = result.scalar_one_or_none()
    
    if active_game:
        # Завершаем игру
        active_game.is_finished = True
        active_game.finished_at = datetime.utcnow()
        await db.commit()
        
        await state.clear()
        
        await message.answer(
            "✅ Активная игра отменена.\n"
            "Теперь вы можете начать новую игру!",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            "ℹ️ У вас нет активных игр",
            reply_markup=get_main_menu_keyboard()
        )