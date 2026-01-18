from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="🎮 Играть"),
        KeyboardButton(text="🏆 Мои достижения")
    )
    builder.row(
        KeyboardButton(text="📋 Правила игры"),
        KeyboardButton(text="💡 Подсказка дня")
    )
    builder.row(
        KeyboardButton(text="⚡ Энергия"),
        KeyboardButton(text="📊 Статистика")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_game_keyboard(has_energy: bool = True, can_use_hint: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура во время игры"""
    builder = InlineKeyboardBuilder()
    
    if can_use_hint:
        builder.row(
            InlineKeyboardButton(
                text="💡 Использовать подсказку (2⚡)", 
                callback_data="game:use_hint"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Сдаться", callback_data="game:surrender")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")
    )
    
    return builder.as_markup()


def get_game_finished_keyboard(is_won: bool) -> InlineKeyboardMarkup:
    """Клавиатура после завершения игры"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🎮 Играть ещё", callback_data="game:play_again")
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Мои достижения", callback_data="menu:achievements"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="menu:stats")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")
    )
    
    return builder.as_markup()


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Админ-панель"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="➕ Добавить ген"),
        KeyboardButton(text="📝 Редактировать ген")
    )
    builder.row(
        KeyboardButton(text="📊 Статистика всех игроков"),
        KeyboardButton(text="🎁 Управление призами")
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в главное меню")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
