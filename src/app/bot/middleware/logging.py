import structlog
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех событий от пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем сообщения
        if isinstance(event, Message):
            user = event.from_user
            
            log_data = {
                "event_type": "message",
                "user_id": user.id,
                "username": user.username or "no_username",
                "full_name": user.full_name,
                "chat_type": event.chat.type,
            }
            
            if event.text:
                log_data["text"] = event.text
                logger.info("📨 User sent message", **log_data)
            
            if event.photo:
                logger.info("📷 User sent photo", **log_data)
            if event.document:
                log_data["file_name"] = event.document.file_name
                logger.info("📄 User sent document", **log_data)
            if event.voice:
                logger.info("🎤 User sent voice", **log_data)
            if event.sticker:
                log_data["sticker_emoji"] = event.sticker.emoji
                logger.info("🎭 User sent sticker", **log_data)
        
        # Логируем callback-запросы (нажатия на кнопки)
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            
            logger.info(
                "🔘 User pressed button",
                event_type="callback",
                user_id=user.id,
                username=user.username or "no_username",
                full_name=user.full_name,
                callback_data=event.data,
            )
        
        # Вызываем обработчик
        try:
            result = await handler(event, data)
            
            # Логируем успешную обработку
            if isinstance(event, Message):
                logger.debug(
                    "✅ Message processed",
                    message_id=event.message_id,
                    user_id=event.from_user.id
                )
            elif isinstance(event, CallbackQuery):
                logger.debug(
                    "✅ Callback processed",
                    callback_id=event.id,
                    user_id=event.from_user.id
                )
            
            return result
            
        except Exception as e:
            # Логируем ошибки
            if isinstance(event, Message):
                logger.error(
                    "❌ Error processing message",
                    message_id=event.message_id,
                    user_id=event.from_user.id,
                    error=str(e),
                    exc_info=True
                )
            elif isinstance(event, CallbackQuery):
                logger.error(
                    "❌ Error processing callback",
                    callback_id=event.id,
                    user_id=event.from_user.id,
                    error=str(e),
                    exc_info=True
                )
            raise