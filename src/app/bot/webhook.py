"""
Webhook обработчик для Telegram бота
"""
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
import logging

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Обработчик webhook запросов"""
    
    def __init__(self, bot: Bot, dp: Dispatcher, secret_token: str = ""):
        self.bot = bot
        self.dp = dp
        self.secret_token = secret_token
        self.handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=secret_token
        )
    
    async def handle(self, request: web.Request) -> web.Response:
        """Обработка входящего webhook запроса"""
        # Проверка secret token
        if self.secret_token:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if token != self.secret_token:
                logger.warning(f"Invalid secret token: {token}")
                return web.Response(status=403, text="Forbidden")
        
        # Передаём обработку SimpleRequestHandler
        return await self.handler.handle(request)


async def setup_webhook(bot: Bot, webhook_url: str, secret_token: str = ""):
    """
    Настройка webhook в Telegram
    
    Args:
        bot: Экземпляр бота
        webhook_url: URL для webhook (https://example.com/webhook/bot)
        secret_token: Секретный токен для валидации запросов
    """
    # Удаляем старый webhook (если есть)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Устанавливаем новый webhook
    await bot.set_webhook(
        url=webhook_url,
        secret_token=secret_token,
        allowed_updates=["message", "callback_query", "inline_query"],
        drop_pending_updates=False
    )
    
    webhook_info = await bot.get_webhook_info()
    logger.info(f"Webhook установлен: {webhook_info.url}")
    logger.info(f"Pending updates: {webhook_info.pending_update_count}")


async def remove_webhook(bot: Bot):
    """Удаление webhook"""
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook удалён")
