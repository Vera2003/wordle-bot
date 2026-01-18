from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..keyboards.menu import get_admin_keyboard, get_main_menu_keyboard, get_cancel_keyboard
from ..states.game import AdminStates
from ...db.models.gene import Gene
from ...db.models.user import User
from ...db.models.game import GameSession
from ...core.config import settings

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда входа в админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    await state.set_state(AdminStates.admin_menu)
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )


@router.message(F.text == "◀️ Назад в главное меню", AdminStates.admin_menu)
async def back_to_menu(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer(
        "🏠 Главное меню",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(F.text == "➕ Добавить ген", AdminStates.admin_menu)
async def add_gene_start(message: Message, state: FSMContext):
    """Начало процесса добавления гена"""
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.adding_gene)
    await state.update_data(step="name")
    
    await message.answer(
        "➕ <b>Добавление нового гена</b>\n\n"
        "Введите название гена (5-7 символов, только латиница и цифры):\n"
        "Например: ADRB2, TCF7L2",
        reply_markup=get_cancel_keyboard()
    )


@router.message(F.text == "❌ Отмена", AdminStates.adding_gene)
async def cancel_adding_gene(message: Message, state: FSMContext):
    """Отмена добавления гена"""
    await state.set_state(AdminStates.admin_menu)
    await message.answer(
        "❌ Добавление отменено",
        reply_markup=get_admin_keyboard()
    )


@router.message(AdminStates.adding_gene)
async def process_adding_gene(message: Message, state: FSMContext, db: AsyncSession):
    """Обработка шагов добавления гена"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    step = data.get("step")
    
    if step == "name":
        # Валидация названия
        name = message.text.strip().upper()
        if not (5 <= len(name) <= 7) or not name.replace("2", "").replace("7", "").isalpha():
            await message.answer(
                "❌ Название должно быть 5-7 символов (латиница и цифры).\n"
                "Попробуйте ещё раз:"
            )
            return
        
        # Проверка уникальности
        query = select(Gene).where(Gene.name == name)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            await message.answer(
                f"❌ Ген <b>{name}</b> уже существует!\n"
                "Введите другое название:"
            )
            return
        
        await state.update_data(name=name, step="description")
        await message.answer(
            f"✅ Название: <b>{name}</b>\n\n"
            "Теперь введите описание гена (что он делает, на что влияет):"
        )
    
    elif step == "description":
        description = message.text.strip()
        if len(description) < 20:
            await message.answer(
                "❌ Описание слишком короткое (минимум 20 символов).\n"
                "Попробуйте ещё раз:"
            )
            return
        
        await state.update_data(description=description, step="hint")
        await message.answer(
            "✅ Описание сохранено\n\n"
            "Введите подсказку для игроков (1-2 предложения):"
        )
    
    elif step == "hint":
        hint = message.text.strip()
        if len(hint) < 10:
            await message.answer(
                "❌ Подсказка слишком короткая (минимум 10 символов).\n"
                "Попробуйте ещё раз:"
            )
            return
        
        await state.update_data(hint=hint, step="difficulty")
        await message.answer(
            "✅ Подсказка сохранена\n\n"
            "Выберите сложность (easy/medium/hard):"
        )
    
    elif step == "difficulty":
        difficulty = message.text.strip().lower()
        if difficulty not in ["easy", "medium", "hard"]:
            await message.answer(
                "❌ Неверная сложность. Выберите: easy, medium или hard"
            )
            return
        
        # Создаём ген
        data = await state.get_data()
        gene = Gene(
            name=data["name"],
            description=data["description"],
            hint=data["hint"],
            difficulty=difficulty,
            is_active=True
        )
        
        db.add(gene)
        await db.commit()
        
        await state.set_state(AdminStates.admin_menu)
        await message.answer(
            f"✅ <b>Ген добавлен успешно!</b>\n\n"
            f"Название: <b>{gene.name}</b>\n"
            f"Сложность: {difficulty}\n"
            f"Описание: {gene.description[:50]}...\n"
            f"Подсказка: {gene.hint[:50]}...",
            reply_markup=get_admin_keyboard()
        )


@router.message(F.text == "📊 Статистика всех игроков", AdminStates.admin_menu)
async def show_global_stats(message: Message, db: AsyncSession):
    """Показывает глобальную статистику"""
    if not is_admin(message.from_user.id):
        return
    
    # Всего пользователей
    total_users_query = select(func.count(User.id))
    total_users = await db.scalar(total_users_query)
    
    # Всего игр
    total_games_query = select(func.count(GameSession.id)).where(
        GameSession.is_finished == True
    )
    total_games = await db.scalar(total_games_query)
    
    # Выигранных игр
    won_games_query = select(func.count(GameSession.id)).where(
        GameSession.is_won == True
    )
    won_games = await db.scalar(won_games_query)
    
    # Всего генов
    total_genes_query = select(func.count(Gene.id))
    total_genes = await db.scalar(total_genes_query)
    
    # Активных генов
    active_genes_query = select(func.count(Gene.id)).where(Gene.is_active == True)
    active_genes = await db.scalar(active_genes_query)
    
    # Топ-3 игрока
    top_players_query = (
        select(User.full_name, User.username, User.total_points)
        .order_by(User.total_points.desc())
        .limit(3)
    )
    result = await db.execute(top_players_query)
    top_players = result.all()
    
    top_text = "\n".join([
        f"{i+1}. {p.full_name or p.username or 'Аноним'}: {p.total_points}🏆"
        for i, p in enumerate(top_players)
    ]) if top_players else "Нет данных"
    
    win_rate = (won_games / total_games * 100) if total_games > 0 else 0
    
    await message.answer(
        f"📊 <b>Глобальная статистика</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🎮 Всего игр: {total_games}\n"
        f"🏆 Выигранных игр: {won_games} ({win_rate:.1f}%)\n"
        f"🧬 Генов в базе: {total_genes} (активных: {active_genes})\n\n"
        f"<b>🏅 Топ-3 игрока:</b>\n{top_text}",
        reply_markup=get_admin_keyboard()
    )


@router.message(F.text == "📝 Редактировать ген", AdminStates.admin_menu)
async def list_genes_for_edit(message: Message, db: AsyncSession):
    """Показывает список генов для редактирования"""
    if not is_admin(message.from_user.id):
        return
    
    query = select(Gene).order_by(Gene.name)
    result = await db.execute(query)
    genes = result.scalars().all()
    
    if not genes:
        await message.answer(
            "❌ В базе нет генов",
            reply_markup=get_admin_keyboard()
        )
        return
    
    genes_list = "\n".join([
        f"{i+1}. {g.name} ({'✅' if g.is_active else '❌'}) - {g.difficulty}"
        for i, g in enumerate(genes)
    ])
    
    await message.answer(
        f"📝 <b>Гены в базе:</b>\n\n{genes_list}\n\n"
        "Используйте /edit_gene [название] для редактирования",
        reply_markup=get_admin_keyboard()
    )
