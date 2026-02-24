"""
Middleware для инъекции текущего пользователя в data['user'].

ВАЖНО: использует get_by_telegram_id (НЕ get_or_create).
Создание пользователя происходит ТОЛЬКО в cmd_start (/start).

Если пользователь написал боту без /start → data['user'] = None,
хендлер отвечает "❌ Используйте /start".

ВАЖНО ПРО AIOGRAM 3:
При регистрации через dp.update.middleware() event — это объект Update,
а НЕ Message/CallbackQuery напрямую. from_user нужно извлекать через
Update.message, Update.callback_query и т.д.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from ...services.user_service import UserService


class UserMiddleware(BaseMiddleware):
    """Добавляет data['user'] (User | None) для всех хендлеров."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        db = data.get("db")
        if not db:
            raise RuntimeError(
                "DB session missing in UserMiddleware. "
                "DbSessionMiddleware must be registered before UserMiddleware."
            )

        # event при dp.update.middleware — это Update, а не Message/CallbackQuery.
        # Извлекаем from_user из конкретного типа события внутри Update.
        from_user = None
        if isinstance(event, Update):
            inner = (
                event.message
                or event.callback_query
                or event.edited_message
                or event.channel_post
                or event.inline_query
            )
            if inner:
                from_user = getattr(inner, "from_user", None)

        if from_user:
            user_service = UserService(db)
            data["user"] = await user_service.get_by_telegram_id(from_user.id)
        else:
            data["user"] = None

        return await handler(event, data)