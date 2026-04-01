from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# from ..keyboards.menu import get_game_keyboard

# def get_game_keyboard(can_use_hint: bool = True) -> InlineKeyboardMarkup:
#     """Клавиатура для игрового процесса"""
#     buttons = [
#         [
#             InlineKeyboardButton(text="🔤 Ввести слово", callback_data="enter_word"),
#         ],
#     ]
    
#     if can_use_hint:
#         buttons.append([
#             InlineKeyboardButton(text="💡 Подсказка", callback_data="get_hint"),
#         ])
    
#     buttons.append([
#         InlineKeyboardButton(text="❌ Сдаться", callback_data="give_up"),
#     ])
    
#     keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
#     return keyboard


def get_game_finished_keyboard(won: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура после завершения игры"""
    text = "🎉 Новая игра" if won else "🎮 Попробовать снова"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=text, callback_data="new_game"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements"),
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        ],
    ])
    return keyboard


def get_difficulty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора сложности"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Легко (5 букв)", callback_data="difficulty_easy"),
        ],
        [
            InlineKeyboardButton(text="🟡 Средне (6 букв)", callback_data="difficulty_medium"),
        ],
        [
            InlineKeyboardButton(text="🔴 Сложно (7 букв)", callback_data="difficulty_hard"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"),
        ],
    ])
    return keyboard


def get_hint_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа подсказки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Описание гена", callback_data="hint_description"),
        ],
        [
            InlineKeyboardButton(text="🔤 Буква в слове", callback_data="hint_letter"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_hint"),
        ],
    ])
    return keyboard