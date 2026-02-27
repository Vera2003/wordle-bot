"""
Хендлеры достижений и статистики.

Исправления:
- Дублирующийся блок isinstance(event, CallbackQuery) заменён на однострочник
- user: User | None инжектируется через UserMiddleware (нет повторного fetch)
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards.menu import get_main_menu_keyboard
from ..texts.messages import ACHIEVEMENTS_MESSAGE, STATS_MESSAGE
from ...db.models.user import User
from ...services.energy_service import EnergyService
from ...services.game_service import GameService

router = Router()


def _get_message(event: Message | CallbackQuery) -> Message:
    """Извлекает объект Message независимо от типа события."""
    return event.message if isinstance(event, CallbackQuery) else event


@router.message(F.text == "📊 Статистика")
@router.callback_query(F.data == "menu:stats")
async def show_stats(
    event: Message | CallbackQuery,
    db: AsyncSession,
    redis,
    user: User | None = None,
):
    message = _get_message(event)

    if not user:
        await message.answer("❌ Используйте /start")
        return

    game_service = GameService(db)
    stats = await game_service.get_user_stats(user.id)

    energy_service = EnergyService(db, redis)
    energy = await energy_service.get_user_energy(user.id)

    text = STATS_MESSAGE.format(
        total_games=stats["total_games"],
        won_games=stats["won_games"],
        lost_games=stats["lost_games"],
        win_rate=stats["win_rate"],
        total_points=stats["total_points"],
        energy=energy,
        achievements_text="🏆 Достижений пока нет",
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        await event.answer()
    else:
        await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(F.text == "🏆 Мои достижения")
@router.callback_query(F.data == "menu:achievements")
async def show_achievements(
    event: Message | CallbackQuery,
    db: AsyncSession,
    user: User | None = None,
):
    message = _get_message(event)

    if not user:
        await message.answer("❌ Используйте /start")
        return

    # TODO: реализовать полную систему достижений
    text = ACHIEVEMENTS_MESSAGE.format(
        achievements_list="Пока нет достижений",
        next_achievement_text="Следующее: 🥈 Серебро (5 побед)",
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        await event.answer()
    else:
        await message.answer(text, reply_markup=get_main_menu_keyboard())