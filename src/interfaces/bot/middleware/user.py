from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from src.interfaces.bot.legacy_facade import get_user_by_telegram_id


class UserMiddleware(BaseMiddleware):

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
            data["user"] = await get_user_by_telegram_id(db, from_user.id)
        else:
            data["user"] = None

        return await handler(event, data)
