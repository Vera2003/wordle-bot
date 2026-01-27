"""
Webhook обработчик для Telegram бота
"""
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import Request, Response
import logging
import json

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Обработчик webhook запросов для FastAPI"""
    
    def __init__(self, bot: Bot, dp: Dispatcher, secret_token: str = ""):
        self.bot = bot
        self.dp = dp
        self.secret_token = secret_token
    
    async def handle(self, request: Request) -> Response:
        """Обработка входящего webhook запроса от Telegram"""
        
        # Проверка secret token
        if self.secret_token:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if token != self.secret_token:
                logger.warning(f"Invalid secret token received")
                return Response(status_code=403, content="Forbidden")
        
        try:
            # Получаем JSON от Telegram
            body = await request.json()
            
            # Создаём Update объект
            update = Update(**body)
            
            # Передаём в диспетчер
            await self.dp.feed_update(bot=self.bot, update=update)
            
            return Response(status_code=200, content="OK")
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return Response(status_code=500, content="Internal Server Error")


async def setup_webhook(bot: Bot, webhook_url: str, secret_token: str = ""):
    """
    Настройка webhook в Telegram
    
    Args:
        bot: Экземпляр бота
        webhook_url: URL для webhook (https://example.com/webhook/bot)
        secret_token: Секретный токен для валидации запросов
    """
    try:
        # Удаляем старый webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Старый webhook удалён")
        
        # Устанавливаем новый webhook
        success = await bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=False
        )
        
        if not success:
            raise RuntimeError("Failed to set webhook")
        
        # Проверяем установку
        webhook_info = await bot.get_webhook_info()
        logger.info(f"✅ Webhook установлен: {webhook_info.url}")
        logger.info(f"Pending updates: {webhook_info.pending_update_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка настройки webhook: {e}", exc_info=True)
        return False


async def remove_webhook(bot: Bot):
    """Удаление webhook"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook удалён")
    except Exception as e:
        logger.error(f"Ошибка удаления webhook: {e}")
