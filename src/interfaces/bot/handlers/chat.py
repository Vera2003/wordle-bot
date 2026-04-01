"""
Хендлер чат-режима с ИИ о генетике.

Пользователь входит в режим через кнопку "🤖 Спросить ИИ",
задаёт вопросы свободным текстом, история сохраняется в FSM.
Выход — кнопка "◀️ Выйти из чата" или команда /start.
"""

from typing import cast

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.bot.legacy_facade import BotUser, answer_genetics_question

from ..states.game import ChatStates
from ..texts.messages import MAIN_MENU_MESSAGE

router = Router()
logger = structlog.get_logger(__name__)

_MAX_HISTORY = 10  # максимум сообщений в FSM-истории


def _get_chat_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="◀️ Выйти из чата"))
    return builder.as_markup(resize_keyboard=True)


# ---------------------------------------------------------------------------
# Вход в чат-режим
# ---------------------------------------------------------------------------


@router.message(F.text == "🤖 Спросить ИИ")
async def enter_chat_mode(
    message: Message,
    state: FSMContext,
    user: BotUser | None = None,
):
    if not user:
        await message.answer("❌ Используйте /start")
        return

    await state.set_state(ChatStates.chatting)
    await state.update_data(chat_history=[])

    await message.answer(
        "🤖 <b>Чат о генетике</b>\n\n"
        "Задавайте любые вопросы о генах, ДНК, наследственности — "
        "я отвечу понятным языком.\n\n"
        "Например:\n"
        "• Что такое ген?\n"
        "• Как работает CRISPR?\n"
        "• Почему дети похожи на родителей?\n\n"
        "Для выхода нажмите <b>◀️ Выйти из чата</b>",
        reply_markup=_get_chat_keyboard(),
    )


# ---------------------------------------------------------------------------
# Выход из чат-режима
# ---------------------------------------------------------------------------


@router.message(F.text == "◀️ Выйти из чата", ChatStates.chatting)
async def exit_chat_mode(message: Message, state: FSMContext):
    from ..keyboards.menu import get_main_menu_keyboard

    await state.clear()
    await message.answer(MAIN_MENU_MESSAGE, reply_markup=get_main_menu_keyboard())


# ---------------------------------------------------------------------------
# Обработка вопроса
# ---------------------------------------------------------------------------


@router.message(ChatStates.chatting, F.text)
async def handle_chat_message(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: BotUser | None = None,
):
    if not user or not message.text:
        return

    question = message.text.strip()
    logger.info("🤖 Chat question", user_id=user.id, question=question[:50])

    # Показываем индикатор печатания
    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action="typing"
    )

    data = await state.get_data()
    history = cast(list[dict[str, str]], data.get("chat_history", []))

    answer = await answer_genetics_question(db, user.id, question, history)

    # Обновляем историю в FSM
    history.append({"role": "user", "text": question})
    history.append({"role": "assistant", "text": answer})

    # Обрезаем историю чтобы не раздувать FSM
    if len(history) > _MAX_HISTORY:
        history = history[-_MAX_HISTORY:]

    await state.update_data(chat_history=history)

    await message.answer(
        f"🤖 {answer}",
        reply_markup=_get_chat_keyboard(),
    )
