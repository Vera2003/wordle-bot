from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🎮 Играть"),
        KeyboardButton(text="🏆 Мои достижения"),
    )
    builder.row(
        KeyboardButton(text="📋 Правила игры"),
        KeyboardButton(text="💡 Подсказка дня"),
    )
    builder.row(
        KeyboardButton(text="⚡ Энергия"),
        KeyboardButton(text="📊 Статистика"),
    )
    builder.row(
        KeyboardButton(text="🤖 Спросить ИИ"),
    )

    return builder.as_markup(resize_keyboard=True)


def get_game_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Сдаться", callback_data="game:surrender"))
    return builder.as_markup()


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Админ-панель."""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="➕ Добавить ген"),
        KeyboardButton(text="📝 Редактировать ген"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика всех игроков"),
        KeyboardButton(text="🎁 Управление призами"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
