"""
Webhook обработчик для Telegram бота
"""
import structlog
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import Request
import hmac
import hashlib

logger = structlog.get_logger(__name__)


class WebhookHandler:
    def __init__(self, bot: Bot, dp: Dispatcher, secret_token: str):
        self.bot = bot
        self.dp = dp
        self.secret_token = secret_token

    async def handle(self, request: Request):
        """Обработка входящих webhook запросов"""
        try:
            # Логируем входящий запрос
            logger.info("🌐 Incoming webhook request")
            
            # Проверка токена
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if token != self.secret_token:
                logger.warning("❌ Invalid secret token", received_token=token)
                return {"status": "error", "message": "Invalid token"}

            # Получаем данные
            data = await request.json()
            logger.info("📦 Webhook data received", update_id=data.get("update_id"))
            
            # Создаём Update объект
            update = Update(**data)
            
            # Передаём в диспетчер
            logger.info("🔄 Feeding update to dispatcher", update_id=update.update_id)
            await self.dp.feed_update(bot=self.bot, update=update)
            
            logger.info("✅ Update processed successfully", update_id=update.update_id)
            return {"status": "ok"}
            
        except Exception as e:
            logger.error("❌ Error processing webhook", error=str(e), exc_info=True)
            return {"status": "error", "message": str(e)}


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
