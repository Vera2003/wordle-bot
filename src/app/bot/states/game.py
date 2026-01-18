from aiogram.fsm.state import State, StatesGroup


class GameStates(StatesGroup):
    """Состояния игрового процесса"""
    
    # Главное меню
    main_menu = State()
    
    # Игровой процесс
    waiting_for_guess = State()  # Ожидание ввода слова
    showing_result = State()     # Показ результата попытки
    game_finished = State()      # Игра завершена
    
    # Подсказка
    viewing_hint = State()


class AdminStates(StatesGroup):
    """Состояния админ-панели"""
    
    admin_menu = State()
    adding_gene = State()
    editing_gene = State()
    viewing_stats = State()
