from aiogram.fsm.state import State, StatesGroup


class GameStates(StatesGroup):
    """Состояния игрового процесса"""

    main_menu = State()
    waiting_for_guess = State()
    showing_result = State()
    game_finished = State()
    viewing_hint = State()


class AdminStates(StatesGroup):
    """Состояния админ-панели"""

    admin_menu = State()
    adding_gene = State()
    editing_gene = State()    # редактирование поля гена
    editing_prize = State()   # редактирование поля приза
    viewing_stats = State()
    
class ChatStates(StatesGroup):
    """Состояния чат-режима с ИИ."""

    chatting = State()