from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards.menu import get_main_menu_keyboard
from ..texts.messages import WELCOME_MESSAGE, MAIN_MENU_MESSAGE, RULES_MESSAGE
from ..states.game import GameStates
from ...db.models.user import User
from ...services.energy_service import EnergyService
from ...core.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession):
    """Обработчик команды /start"""
    # Создаём или получаем пользователя
    user = await db.get(User, message.from_user.id)
    
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


@router.message(F.text == "⚡ Энергия")
async def show_energy(
    message: Message, 
    db: AsyncSession,
    redis
):
    """Показывает информацию об энергии"""
    from ..texts.messages import ENERGY_MESSAGE
    
    energy_service = EnergyService(db, redis)
    
    # Получаем пользователя
    user = await db.get(User, message.from_user.id)
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
