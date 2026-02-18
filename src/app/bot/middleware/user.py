from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from ...services.user_service import UserService


class UserMiddleware(BaseMiddleware):
    """
    Middleware для загрузки/создания пользователя по Telegram ID
    и передачи объекта User в хендлеры через data['user'].
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        db = data.get('db')
        if not db:
            raise RuntimeError("Db session is missing in UserMiddleware. Make sure DbSessionMiddleware is applied first.")

        user_service = UserService(db)
        telegram_id = None
        username = None
        full_name = None

        # Получаем данные пользователя из события
        if isinstance(event, Message) or isinstance(event, CallbackQuery):
            tg_user = event.from_user
            telegram_id = tg_user.id
            username = tg_user.username
            full_name = tg_user.full_name

        if telegram_id:
            # Получаем или создаём пользователя
            user = await user_service.get_or_create(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name
            )
            data['user'] = user  # передаем в хендлер
        else:
            data['user'] = None

        # Продолжаем цепочку обработки
        return await handler(event, data)
