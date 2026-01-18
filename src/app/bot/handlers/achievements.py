from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards.menu import get_main_menu_keyboard
from ..texts.messages import STATS_MESSAGE, ACHIEVEMENTS_MESSAGE
from ...db.models.user import User
from ...services.game_service import GameService
from ...services.energy_service import EnergyService

router = Router()


@router.message(F.text == "📊 Статистика")
@router.callback_query(F.data == "menu:stats")
async def show_stats(
    event: Message | CallbackQuery,
    db: AsyncSession,
    redis
):
    """Показывает статистику пользователя"""
    # Определяем тип события
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    else:
        user_id = event.from_user.id
        message = event
    
    # Получаем пользователя
    user = await db.get(User, user_id)
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    # Получаем статистику
    game_service = GameService(db)
    stats = await game_service.get_user_stats(user.id)
    
    # Получаем энергию
    energy_service = EnergyService(db, redis)
    energy = await energy_service.get_user_energy(user.id)
    
    # TODO: получить достижения
    achievements_text = "🏆 Достижений пока нет"
    
    text = STATS_MESSAGE.format(
        total_games=stats['total_games'],
        won_games=stats['won_games'],
        lost_games=stats['lost_games'],
        win_rate=stats['win_rate'],
        total_points=stats['total_points'],
        energy=energy,
        achievements_text=achievements_text
    )
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        await event.answer()
    else:
        await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(F.text == "🏆 Мои достижения")
@router.callback_query(F.data == "menu:achievements")
async def show_achievements(event: Message | CallbackQuery, db: AsyncSession):
    """Показывает достижения пользователя"""
    # Определяем тип события
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    else:
        user_id = event.from_user.id
        message = event
    
    # TODO: реализовать систему достижений
    achievements_list = "Пока нет достижений"
    next_achievement_text = "Следующее: 🥈 Серебро (5 побед)"
    
    text = ACHIEVEMENTS_MESSAGE.format(
        achievements_list=achievements_list,
        next_achievement_text=next_achievement_text
    )
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        await event.answer()
    else:
        await message.answer(text, reply_markup=get_main_menu_keyboard())
