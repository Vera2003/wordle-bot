"""
Хендлеры админ-панели.

Исправления:
- ADMIN_IDS больше не хардкодится — используется settings.admin_ids
- Статистика делегирована StatsService (убрано дублирование SQL-запросов)
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards.menu import get_admin_keyboard, get_cancel_keyboard, get_main_menu_keyboard
from ..states.game import AdminStates
from ...core.config import settings
from ...db.models.gene import Gene
from ...services.stats_service import StatsService

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора")
        return

    await state.set_state(AdminStates.admin_menu)
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
    )


@router.message(F.text == "◀️ Назад в главное меню", AdminStates.admin_menu)
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=get_main_menu_keyboard())


@router.message(F.text == "➕ Добавить ген", AdminStates.admin_menu)
async def add_gene_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(AdminStates.adding_gene)
    await state.update_data(step="name")

    await message.answer(
        "➕ <b>Добавление нового гена</b>\n\n"
        "Введите название гена (5-7 символов, только латиница и цифры):\n"
        "Например: ADRB2, TCF7L2",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(F.text == "❌ Отмена", AdminStates.adding_gene)
async def cancel_adding_gene(message: Message, state: FSMContext):
    await state.set_state(AdminStates.admin_menu)
    await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())


@router.message(AdminStates.adding_gene)
async def process_adding_gene(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    step = data.get("step")

    if step == "name":
        name = message.text.strip().upper()
        # Простая проверка: 5-7 символов, только A-Z и цифры
        clean = name.replace("0", "").replace("1", "").replace("2", "").replace(
            "3", "").replace("4", "").replace("5", "").replace("6", "").replace(
            "7", "").replace("8", "").replace("9", "")
        if not (5 <= len(name) <= 7) or not clean.isalpha():
            await message.answer(
                "❌ Название должно быть 5-7 символов (латиница и цифры).\nПопробуйте ещё раз:"
            )
            return

        result = await db.execute(select(Gene).where(Gene.name == name))
        if result.scalar_one_or_none():
            await message.answer(
                f"❌ Ген <b>{name}</b> уже существует!\nВведите другое название:"
            )
            return

        await state.update_data(name=name, step="description")
        await message.answer(
            f"✅ Название: <b>{name}</b>\n\nТеперь введите описание гена:"
        )

    elif step == "description":
        description = message.text.strip()
        if len(description) < 20:
            await message.answer("❌ Описание слишком короткое (минимум 20 символов).\nПопробуйте ещё раз:")
            return

        await state.update_data(description=description, step="hint")
        await message.answer("✅ Описание сохранено\n\nВведите подсказку для игроков (1-2 предложения):")

    elif step == "hint":
        hint = message.text.strip()
        if len(hint) < 10:
            await message.answer("❌ Подсказка слишком короткая (минимум 10 символов).\nПопробуйте ещё раз:")
            return

        await state.update_data(hint=hint, step="difficulty")
        await message.answer("✅ Подсказка сохранена\n\nВыберите сложность (easy/medium/hard):")

    elif step == "difficulty":
        difficulty = message.text.strip().lower()
        if difficulty not in ("easy", "medium", "hard"):
            await message.answer("❌ Неверная сложность. Выберите: easy, medium или hard")
            return

        data = await state.get_data()
        gene = Gene(
            name=data["name"],
            description=data["description"],
            hint=data["hint"],
            difficulty=difficulty,
            is_active=True,
        )
        db.add(gene)
        await db.commit()

        await state.set_state(AdminStates.admin_menu)
        await message.answer(
            f"✅ <b>Ген добавлен успешно!</b>\n\n"
            f"Название: <b>{gene.name}</b>\n"
            f"Сложность: {difficulty}",
            reply_markup=get_admin_keyboard(),
        )


@router.message(F.text == "📊 Статистика всех игроков", AdminStates.admin_menu)
async def show_global_stats(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    stats = await StatsService(db).get_global()

    top_text = "\n".join(
        f"{i + 1}. {p['name']}: {p['points']}🏆"
        for i, p in enumerate(stats["top_players"][:3])
    ) or "Нет данных"

    await message.answer(
        f"📊 <b>Глобальная статистика</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🎮 Всего игр: {stats['total_games']}\n"
        f"🏆 Выигранных игр: {stats['won_games']} ({stats['win_rate']}%)\n"
        f"🧬 Генов в базе: {stats['total_genes']} (активных: {stats['active_genes']})\n\n"
        f"<b>🏅 Топ-3 игрока:</b>\n{top_text}",
        reply_markup=get_admin_keyboard(),
    )


@router.message(F.text == "📝 Редактировать ген", AdminStates.admin_menu)
async def list_genes_for_edit(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    result = await db.execute(select(Gene).order_by(Gene.name))
    genes = result.scalars().all()

    if not genes:
        await message.answer("❌ В базе нет генов", reply_markup=get_admin_keyboard())
        return

    genes_list = "\n".join(
        f"{i + 1}. {g.name} ({'✅' if g.is_active else '❌'}) - {g.difficulty}"
        for i, g in enumerate(genes)
    )
    await message.answer(
        f"📝 <b>Гены в базе:</b>\n\n{genes_list}\n\n"
        "Используйте /edit_gene [название] для редактирования",
        reply_markup=get_admin_keyboard(),
    )