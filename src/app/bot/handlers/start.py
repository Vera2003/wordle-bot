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
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards.menu import get_main_menu_keyboard
from ..states.game import GameStates
from ..texts.messages import ENERGY_MESSAGE, MAIN_MENU_MESSAGE, RULES_MESSAGE, WELCOME_MESSAGE
from ...core.config import settings
from ...db.models.achievements import UserAchievement
from ...db.models.game import GameSession
from ...db.models.prize import UserPrize
from ...db.models.user import User
from ...services.energy_service import EnergyService
from ...services.gene_of_day_service import GeneOfDayService
from ...services.hint_service import HintService
from ...services.user_service import UserService
from ...utils.time_helpers import get_today_str

router = Router()
logger = structlog.get_logger(__name__)


@router.message(Command("resetday"))
async def cmd_reset_day(
    message: Message,
    db: AsyncSession,
    redis,
    user: User | None = None,
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

    # Инвалидируем ген дня через сервис (единая точка)
    gene_of_day_service = GeneOfDayService(db, redis)
    await gene_of_day_service.invalidate()

    # Сбрасываем счётчик подсказок
    await redis.delete(f"user:{user.id}:daily_hints:{get_today_str()}")

    # Удаляем все игровые данные пользователя
    await db.execute(delete(GameSession).where(GameSession.user_id == user.id))
    await db.execute(delete(UserAchievement).where(UserAchievement.user_id == user.id))
    await db.execute(delete(UserPrize).where(UserPrize.user_id == user.id))
    user.total_points = 0
    await db.commit()

    # Восстанавливаем энергию
    energy_service = EnergyService(db, redis)
    await energy_service.restore_daily_energy(user.id)

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
    user: User | None = None,
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
        user_service = UserService(db)
        user = await user_service.get_or_create(
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
    user: User | None = None,
):
    if not user:
        await message.answer("❌ Используйте /start")
        return

    hint_service = HintService(db, redis)
    result = await hint_service.show_hint(user.id, hint_type="daily")

    # show_hint возвращает {"success": True, "text": ...} или {"success": False, "message": ...}
    text = result.get("text") or result.get("message") or "❌ Ошибка"
    await message.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(F.text == "⚡ Энергия")
async def show_energy(
    message: Message,
    db: AsyncSession,
    redis,
    user: User | None = None,
):
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start")
        return

    energy_service = EnergyService(db, redis)
    current_energy = await energy_service.get_user_energy(user.id)

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
    user: User | None = None,
):
    """Отменить зависшую активную игру."""
    if not user:
        await message.answer("❌ Используйте /start")
        return

    result = await db.execute(
        select(GameSession).where(
            GameSession.user_id == user.id,
            GameSession.is_finished == False,
        )
    )
    active_game = result.scalar_one_or_none()

    if active_game:
        active_game.is_finished = True
        active_game.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        await state.clear()
        await message.answer(
            "✅ Активная игра отменена.\nТеперь вы можете начать новую игру!",
            reply_markup=get_main_menu_keyboard(),
        )
    else:
        await message.answer("ℹ️ У вас нет активных игр", reply_markup=get_main_menu_keyboard())