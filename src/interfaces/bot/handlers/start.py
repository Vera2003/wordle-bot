"""
Хендлеры стартового меню и системных команд.

Исправления:
- cmd_start получает user из data['user'] (UserMiddleware), не создаёт повторно
  ИСКЛЮЧЕНИЕ: если user is None — создаём (это первый /start)
- show_daily_hint, show_energy, cmd_cancel_game — user из UserMiddleware
- cmd_reset_day — использует GeneOfDayService.invalidate() вместо прямого redis.delete()
- Все импорты на уровне модуля, не внутри функций
- Добавлен /help как алиас для правил
"""
from datetime import datetime, timezone

import structlog
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.bot.legacy_facade import (
    BotUser,
    cancel_active_game_for_user,
    get_or_create_user,
    get_user_energy,
    reset_user_daily_state,
    show_daily_hint as facade_show_daily_hint,
)
from ..keyboards.menu import get_main_menu_keyboard
from ..states.game import GameStates
from ..texts.messages import ENERGY_MESSAGE, MAIN_MENU_MESSAGE, RULES_MESSAGE, WELCOME_MESSAGE
from src.core.config import get_settings

router = Router()
logger = structlog.get_logger(__name__)
settings = get_settings()

@router.message(Command("resetday"))
async def cmd_reset_day(
    message: Message,
    db: AsyncSession,
    redis,
    user: BotUser | None = None,
):
    """Dev-команда: полный сброс дня. Только для админов."""
    if message.from_user is None:
        return
    if message.from_user.id not in settings.admin_ids:
        # await message.answer("❌ У вас нет доступа к этой команде")
        return

    if not user:
        await message.answer("❌ Используйте /start")
        return

    await reset_user_daily_state(db, redis, user.id)

    await message.answer(
        "✅ <b>День сброшен!</b>\n\n"
        "• Слово дня удалено\n"
        "• Счётчик подсказок обнулён\n"
        "• Игровые данные удалены\n"
        "• Энергия восстановлена\n\n"
        "Теперь можете начать новую игру с новым словом!",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: BotUser | None = None,
):
    """
    /start — единственный хендлер, который создаёт пользователя.

    UserMiddleware уже попробовал найти пользователя.
    Если user is None — это первый запуск, создаём через get_or_create.
    Если user уже есть — просто показываем меню.
    """
    if user is None:
        if message.from_user is None:
            await message.answer("❌ Не удалось определить пользователя")
            return
        user = await get_or_create_user(
            db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        logger.info("👤 New user registered", telegram_id=message.from_user.id)

    await state.set_state(GameStates.main_menu)
    await message.answer(
        WELCOME_MESSAGE.format(energy=settings.daily_energy),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "🏠 Главное меню")
@router.callback_query(F.data == "menu:main")
async def show_main_menu(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.main_menu)

    if isinstance(event, CallbackQuery):
        # edit_text принимает только InlineKeyboardMarkup, но главное меню —
        # ReplyKeyboardMarkup. Удаляем старое сообщение и отправляем новое.
        if isinstance(event.message, Message):
            await event.message.delete()
        await event.answer()
        await event.bot.send_message(  # type: ignore[union-attr]
            chat_id=event.from_user.id,
            text=MAIN_MENU_MESSAGE,
            reply_markup=get_main_menu_keyboard(),
        )
    else:
        await event.answer(MAIN_MENU_MESSAGE, reply_markup=get_main_menu_keyboard())


@router.message(F.text == "📋 Правила игры")
@router.message(Command("help"))
async def show_rules(message: Message):
    await message.answer(
        RULES_MESSAGE.format(daily_energy=settings.daily_energy),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "💡 Подсказка дня")
async def show_daily_hint(
    message: Message,
    db: AsyncSession,
    redis,
    user: BotUser | None = None,
):
    if not user:
        await message.answer("❌ Используйте /start")
        return

    result = await facade_show_daily_hint(db, redis, user.id)

    # show_hint возвращает {"success": True, "text": ...} или {"success": False, "message": ...}
    text = result.get("text") or result.get("message") or "❌ Ошибка"
    await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(F.text == "⚡ Энергия")
async def show_energy(
    message: Message,
    db: AsyncSession,
    redis,
    user: BotUser | None = None,
):
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start")
        return

    current_energy = await get_user_energy(db, redis, user.id)

    await message.answer(
        ENERGY_MESSAGE.format(
            current_energy=current_energy,
            max_energy=settings.daily_energy,
            daily_energy=settings.daily_energy,
        ),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("cancel"))
async def cmd_cancel_game(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: BotUser | None = None,
):
    """Отменить зависшую активную игру."""
    if not user:
        await message.answer("❌ Используйте /start")
        return

    if await cancel_active_game_for_user(db, user.id):
        await state.clear()
        await message.answer(
            "✅ Активная игра отменена.\nТеперь вы можете начать новую игру!",
            reply_markup=get_main_menu_keyboard(),
        )
    else:
        await message.answer("ℹ️ У вас нет активных игр", reply_markup=get_main_menu_keyboard())