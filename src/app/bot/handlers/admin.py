"""
Хендлеры админ-панели.

Исправления и дополнения:
- ADMIN_IDS не хардкодится — используется settings.admin_ids
- Статистика делегирована StatsService
- Добавлено редактирование генов (FSM: AdminStates.editing_gene)
- Добавлено управление призами (просмотр, активация/деактивация)
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards.menu import (
    get_admin_keyboard,
    get_cancel_keyboard,
    get_main_menu_keyboard,
)
from ..states.game import AdminStates
from ...core.config import settings
from ...db.models.gene import Gene
from ...db.models.prize import PrizeType
from ...services.stats_service import StatsService

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


# ============================================================================
# ВХОД В ПАНЕЛЬ
# ============================================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user is None:
        return
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


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.message(F.text == "📊 Статистика всех игроков", AdminStates.admin_menu)
async def show_global_stats(message: Message, db: AsyncSession):
    if message.from_user is None:
        return
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
        f"🏆 Выигранных: {stats['won_games']} ({stats['win_rate']}%)\n"
        f"🧬 Генов в базе: {stats['total_genes']} (активных: {stats['active_genes']})\n\n"
        f"<b>🏅 Топ-3 игрока:</b>\n{top_text}",
        reply_markup=get_admin_keyboard(),
    )


# ============================================================================
# ДОБАВЛЕНИЕ ГЕНА
# ============================================================================

@router.message(F.text == "➕ Добавить ген", AdminStates.admin_menu)
async def add_gene_start(message: Message, state: FSMContext):
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id):
        return

    await state.set_state(AdminStates.adding_gene)
    await state.update_data(step="name")
    await message.answer(
        "➕ <b>Добавление нового гена</b>\n\n"
        "Введите название гена (5-7 символов, латиница и цифры):\n"
        "Например: ADRB2, TCF7L2",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(F.text == "❌ Отмена", AdminStates.adding_gene)
async def cancel_adding_gene(message: Message, state: FSMContext):
    await state.set_state(AdminStates.admin_menu)
    await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())


@router.message(AdminStates.adding_gene)
async def process_adding_gene(message: Message, state: FSMContext, db: AsyncSession):
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id):
        return
    if message.text is None:
        return

    data = await state.get_data()
    step = data.get("step")

    if step == "name":
        name = message.text.strip().upper()
        clean = "".join(c for c in name if c.isalpha())
        if not (5 <= len(name) <= 7) or not clean.isalpha():
            await message.answer(
                "❌ Название должно быть 5-7 символов (латиница и цифры).\nПопробуйте ещё раз:"
            )
            return
        result = await db.execute(select(Gene).where(Gene.name == name))
        if result.scalar_one_or_none():
            await message.answer(f"❌ Ген <b>{name}</b> уже существует!\nВведите другое название:")
            return
        await state.update_data(name=name, step="description")
        await message.answer(f"✅ Название: <b>{name}</b>\n\nВведите описание гена:")

    elif step == "description":
        description = message.text.strip()
        if len(description) < 20:
            await message.answer("❌ Описание слишком короткое (минимум 20 символов).\nПопробуйте ещё раз:")
            return
        await state.update_data(description=description, step="hint")
        await message.answer("✅ Описание сохранено\n\nВведите подсказку для игроков:")

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
            f"✅ <b>Ген добавлен!</b>\n\n"
            f"Название: <b>{gene.name}</b>\n"
            f"Сложность: {difficulty}",
            reply_markup=get_admin_keyboard(),
        )


# ============================================================================
# РЕДАКТИРОВАНИЕ ГЕНА
# ============================================================================

@router.message(F.text == "📝 Редактировать ген", AdminStates.admin_menu)
async def list_genes_for_edit(message: Message, state: FSMContext, db: AsyncSession):
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id):
        return

    result = await db.execute(select(Gene).order_by(Gene.name))
    genes = result.scalars().all()

    if not genes:
        await message.answer("❌ В базе нет генов", reply_markup=get_admin_keyboard())
        return

    # Inline-кнопки с каждым геном
    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅' if g.is_active else '❌'} {g.name} [{g.difficulty}]",
            callback_data=f"admin:edit_gene:{g.id}"
        )]
        for g in genes
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "📝 <b>Выберите ген для редактирования:</b>\n\n"
        "✅ — активен, ❌ — деактивирован",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("admin:edit_gene:"))
async def show_gene_edit_menu(callback: CallbackQuery, db: AsyncSession):
    if not callback.data:
        await callback.answer("Неверные данные", show_alert=True)
        return
    gene_id = int(callback.data.split(":")[-1])
    gene = await db.get(Gene, gene_id)
    if not gene:
        await callback.answer("Ген не найден", show_alert=True)
        return

    status = "✅ Активен" if gene.is_active else "❌ Деактивирован"
    toggle_text = "❌ Деактивировать" if gene.is_active else "✅ Активировать"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"admin:gene_field:description:{gene_id}")],
        [InlineKeyboardButton(text="💡 Изменить подсказку",  callback_data=f"admin:gene_field:hint:{gene_id}")],
        [InlineKeyboardButton(text="📊 Изменить сложность", callback_data=f"admin:gene_field:difficulty:{gene_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:gene_toggle:{gene_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin:back_to_genes")],
    ])

    text = (
        f"🧬 <b>Ген {gene.name}</b>\n\n"
        f"Статус: {status}\n"
        f"Сложность: {gene.difficulty}\n\n"
        f"<b>Описание:</b>\n{gene.description}\n\n"
        f"<b>Подсказка:</b>\n{gene.hint}"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin:back_to_genes")
async def back_to_genes(callback: CallbackQuery, db: AsyncSession):
    result = await db.execute(select(Gene).order_by(Gene.name))
    genes = result.scalars().all()

    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅' if g.is_active else '❌'} {g.name} [{g.difficulty}]",
            callback_data=f"admin:edit_gene:{g.id}"
        )]
        for g in genes
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "📝 <b>Выберите ген для редактирования:</b>\n\n✅ — активен, ❌ — деактивирован",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:gene_toggle:"))
async def toggle_gene_active(callback: CallbackQuery, db: AsyncSession):
    if not callback.data:
        await callback.answer("Неверные данные", show_alert=True)
        return
    gene_id = int(callback.data.split(":")[-1])
    gene = await db.get(Gene, gene_id)
    if not gene:
        await callback.answer("Ген не найден", show_alert=True)
        return

    gene.is_active = not gene.is_active
    await db.commit()

    status = "активирован ✅" if gene.is_active else "деактивирован ❌"
    await callback.answer(f"Ген {gene.name} {status}", show_alert=True)

    # Обновляем меню редактирования
    await show_gene_edit_menu(callback, db)


@router.callback_query(F.data.startswith("admin:gene_field:"))
async def start_edit_gene_field(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Начать редактирование конкретного поля гена."""
    if not callback.data:
        await callback.answer("Неверные данные", show_alert=True)
        return
    parts = callback.data.split(":")  # admin:gene_field:FIELD:GENE_ID
    field = parts[2]
    gene_id = int(parts[3])

    gene = await db.get(Gene, gene_id)
    if not gene:
        await callback.answer("Ген не найден", show_alert=True)
        return

    field_labels = {
        "description": "описание",
        "hint": "подсказку",
        "difficulty": "сложность (easy/medium/hard)",
    }

    await state.set_state(AdminStates.editing_gene)
    await state.update_data(edit_gene_id=gene_id, edit_field=field)

    if isinstance(callback.message, Message):
        await callback.message.answer(
            f"✏️ Введите новое {field_labels.get(field, field)} для гена <b>{gene.name}</b>:\n\n"
            f"<i>Текущее значение:</i> {getattr(gene, field)}",
            reply_markup=get_cancel_keyboard(),
        )
    await callback.answer()


@router.message(F.text == "❌ Отмена", AdminStates.editing_gene)
async def cancel_editing_gene(message: Message, state: FSMContext):
    await state.set_state(AdminStates.admin_menu)
    await message.answer("❌ Редактирование отменено", reply_markup=get_admin_keyboard())


@router.message(AdminStates.editing_gene)
async def process_edit_gene_field(message: Message, state: FSMContext, db: AsyncSession):
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id):
        return
    if message.text is None:
        return

    data = await state.get_data()
    gene_id: int | None = data.get("edit_gene_id")
    field: str | None = data.get("edit_field")

    if not gene_id or not field:
        await message.answer("❌ Данные сессии потеряны")
        await state.set_state(AdminStates.admin_menu)
        return

    gene = await db.get(Gene, gene_id)
    if not gene:
        await message.answer("❌ Ген не найден")
        await state.set_state(AdminStates.admin_menu)
        return

    value = message.text.strip()

    # Валидация по полю
    if field == "description" and len(value) < 20:
        await message.answer("❌ Описание слишком короткое (минимум 20 символов). Попробуйте ещё раз:")
        return
    if field == "hint" and len(value) < 10:
        await message.answer("❌ Подсказка слишком короткая (минимум 10 символов). Попробуйте ещё раз:")
        return
    if field == "difficulty" and value.lower() not in ("easy", "medium", "hard"):
        await message.answer("❌ Допустимые значения: easy, medium, hard. Попробуйте ещё раз:")
        return

    if field == "difficulty":
        value = value.lower()

    setattr(gene, field, value)
    await db.commit()

    await state.set_state(AdminStates.admin_menu)
    await message.answer(
        f"✅ <b>Ген {gene.name} обновлён!</b>\n\n"
        f"Поле <b>{field}</b> изменено.",
        reply_markup=get_admin_keyboard(),
    )


# ============================================================================
# УПРАВЛЕНИЕ ПРИЗАМИ
# ============================================================================

@router.message(F.text == "🎁 Управление призами", AdminStates.admin_menu)
async def show_prizes(message: Message, state: FSMContext, db: AsyncSession):
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id):
        return

    result = await db.execute(select(PrizeType).order_by(PrizeType.name))
    prizes = result.scalars().all()

    if not prizes:
        await message.answer("❌ Призы не найдены в базе. Запустите task db-init", reply_markup=get_admin_keyboard())
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅' if p.is_active else '❌'} {p.title}",
            callback_data=f"admin:prize:{p.id}"
        )]
        for p in prizes
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "🎁 <b>Управление призами</b>\n\n"
        "Нажмите на приз для просмотра и изменения статуса:\n"
        "✅ — активен (доступен игрокам), ❌ — деактивирован",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("admin:prize:"))
async def show_prize_detail(callback: CallbackQuery, db: AsyncSession):
    if not callback.data:
        await callback.answer("Неверные данные", show_alert=True)
        return
    prize_id = int(callback.data.split(":")[-1])
    prize = await db.get(PrizeType, prize_id)
    if not prize:
        await callback.answer("Приз не найден", show_alert=True)
        return

    status = "✅ Активен" if prize.is_active else "❌ Деактивирован"
    toggle_text = "❌ Деактивировать" if prize.is_active else "✅ Активировать"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:prize_toggle:{prize_id}")],
        [InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"admin:prize_field:description:{prize_id}")],
        [InlineKeyboardButton(text="🔑 Изменить промокод/значение", callback_data=f"admin:prize_field:prize_value:{prize_id}")],
        [InlineKeyboardButton(text="◀️ Назад к призам", callback_data="admin:back_to_prizes")],
    ])

    text = (
        f"🎁 <b>{prize.title}</b>\n\n"
        f"Статус: {status}\n"
        f"Промокод / значение: <code>{prize.prize_value}</code>\n\n"
        f"<b>Описание:</b>\n{prize.description}"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin:back_to_prizes")
async def back_to_prizes(callback: CallbackQuery, db: AsyncSession):
    result = await db.execute(select(PrizeType).order_by(PrizeType.name))
    prizes = result.scalars().all()

    buttons = [
        [InlineKeyboardButton(
            text=f"{'✅' if p.is_active else '❌'} {p.title}",
            callback_data=f"admin:prize:{p.id}"
        )]
        for p in prizes
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🎁 <b>Управление призами</b>\n\n"
            "✅ — активен, ❌ — деактивирован",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:prize_toggle:"))
async def toggle_prize_active(callback: CallbackQuery, db: AsyncSession):
    if not callback.data:
        await callback.answer("Неверные данные", show_alert=True)
        return
    prize_id = int(callback.data.split(":")[-1])
    prize = await db.get(PrizeType, prize_id)
    if not prize:
        await callback.answer("Приз не найден", show_alert=True)
        return

    prize.is_active = not prize.is_active
    await db.commit()

    status = "активирован ✅" if prize.is_active else "деактивирован ❌"
    await callback.answer(f"Приз «{prize.title}» {status}", show_alert=True)

    await show_prize_detail(callback, db)


@router.callback_query(F.data.startswith("admin:prize_field:"))
async def start_edit_prize_field(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    if not callback.data:
        await callback.answer("Неверные данные", show_alert=True)
        return
    parts = callback.data.split(":")  # admin:prize_field:FIELD:PRIZE_ID
    field = parts[2]
    prize_id = int(parts[3])

    prize = await db.get(PrizeType, prize_id)
    if not prize:
        await callback.answer("Приз не найден", show_alert=True)
        return

    field_labels = {
        "description": "описание",
        "prize_value": "промокод/значение",
    }

    await state.set_state(AdminStates.editing_prize)
    await state.update_data(edit_prize_id=prize_id, edit_field=field)

    if isinstance(callback.message, Message):
        await callback.message.answer(
            f"✏️ Введите новое {field_labels.get(field, field)} для приза <b>{prize.title}</b>:\n\n"
            f"<i>Текущее значение:</i> {getattr(prize, field)}",
            reply_markup=get_cancel_keyboard(),
        )
    await callback.answer()


@router.message(F.text == "❌ Отмена", AdminStates.editing_prize)
async def cancel_editing_prize(message: Message, state: FSMContext):
    await state.set_state(AdminStates.admin_menu)
    await message.answer("❌ Редактирование отменено", reply_markup=get_admin_keyboard())


@router.message(AdminStates.editing_prize)
async def process_edit_prize_field(message: Message, state: FSMContext, db: AsyncSession):
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id):
        return
    if message.text is None:
        return

    data = await state.get_data()
    prize_id = data.get("edit_prize_id")
    field: str | None = data.get("edit_field")
    
    if not field:
        await message.answer("❌ Поле не определено")
        await state.set_state(AdminStates.admin_menu)
        return

    prize = await db.get(PrizeType, prize_id)
    if not prize:
        await message.answer("❌ Приз не найден")
        await state.set_state(AdminStates.admin_menu)
        return

    value = message.text.strip()

    if field == "description" and len(value) < 10:
        await message.answer("❌ Описание слишком короткое (минимум 10 символов). Попробуйте ещё раз:")
        return
    if field == "prize_value" and len(value) < 2:
        await message.answer("❌ Значение слишком короткое. Попробуйте ещё раз:")
        return

    setattr(prize, field, value)
    await db.commit()

    await state.set_state(AdminStates.admin_menu)
    await message.answer(
        f"✅ <b>Приз «{prize.title}» обновлён!</b>",
        reply_markup=get_admin_keyboard(),
    )