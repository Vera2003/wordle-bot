from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis
import random

from ..db.models.gene import Gene
from ..db.models.user import User
from ..db.models.game import GameSession
from ..core.config import settings
from ..utils.time_helpers import get_seconds_until_midnight, get_today_str, get_today_date

class HintService:
    """Сервис управления подсказками"""
    
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis
    
    async def get_daily_hint_count(self, user_id: int) -> int:
        """Получить количество использованных подсказок дня"""
        today = get_today_str()
        key = f"user:{user_id}:daily_hints:{today}"
        count = await self.redis.get(key)
        return int(count) if count else 0
    
    async def increment_daily_hint(self, user_id: int):
        """Увеличить счетчик подсказок дня"""
        today = get_today_str()
        key = f"user:{user_id}:daily_hints:{today}"
        ttl = get_seconds_until_midnight()
        
        current = await self.get_daily_hint_count(user_id)
        await self.redis.set(key, current + 1, ex=ttl)
    
    async def get_gene_of_day(self) -> Gene:
        """
        Получить ген дня (или выбрать случайный, если его нет)
        
        Логика:
        1. Проверяем Redis кэш по ключу "gene_of_day:YYYY-MM-DD"
        2. Если есть - загружаем из БД по ID
        3. Если нет - выбираем случайный активный ген
        4. Сохраняем в Redis с TTL до конца дня
        
        Returns:
            Gene: Ген дня
        
        Raises:
            ValueError: Если в БД нет активных генов
        """
        today = get_today_str()
        gene_key = f"gene_of_day:{today}"
        
        # Проверяем кэш Redis
        cached_gene_id = await self.redis.get(gene_key)
        
        if cached_gene_id:
            # Ген дня уже выбран ранее
            gene_id = int(cached_gene_id)
            gene = await self.db.get(Gene, gene_id)
            
            if gene and gene.is_active:
                return gene
            
            # Если ген удалён/деактивирован, выбираем новый
            await self.redis.delete(gene_key)
        
        # Выбираем случайный активный ген
        query = select(Gene).where(Gene.is_active == True)
        result = await self.db.execute(query)
        genes = result.scalars().all()
        
        if not genes:
            raise ValueError("В базе данных нет доступных генов")
        
        # Случайный выбор
        gene = random.choice(genes)
        
        # Сохраняем в Redis до конца дня (00:00 UTC)
        ttl = get_seconds_until_midnight()
        await self.redis.set(gene_key, gene.id, ex=ttl)
        
        return gene
    
    async def show_hint(self, user_id: int, hint_type: str = "auto") -> dict:
        """
        Показать подсказку пользователю
        
        Args:
            user_id: ID пользователя в БД (не telegram_id!)
            hint_type: Тип подсказки (не используется пока, для будущего)
        
        Returns:
            dict: {
                "success": bool,
                "hint_number": int (1 или 2),
                "text": str (HTML-текст подсказки),
                "error": str (если success=False),
                "message": str (если success=False)
            }
        """
        gene = await self.get_gene_of_day()
        hints_used = await self.get_daily_hint_count(user_id)
        
        # Проверяем, есть ли завершенная игра сегодня
        today = get_today_date()
        
        finished_query = select(GameSession).where(
            GameSession.user_id == user_id,
            GameSession.is_finished == True,
            func.date(GameSession.started_at) == today
        )
        result = await self.db.execute(finished_query)
        finished_game = result.scalar_one_or_none()
        
        if finished_game:
            outcome = "угадали слово" if finished_game.is_won else "исчерпали все попытки"
            return {
                "success": False,
                "error": "game_finished",
                "message": (
                    f"🔒 <b>Подсказки недоступны</b>\n\n"
                    f"Вы уже завершили игру на сегодня — вы {outcome}.\n"
                    f"Новая игра и подсказки будут доступны завтра в 00:00 🌙"
                )
            }
        
        # Дневной лимит (2 бесплатные подсказки)
        if hints_used >= 2:
            return {
                "success": False,
                "error": "daily_limit",
                "message": (
                    "💡 <b>Подсказки дня исчерпаны</b>\n\n"
                    "Вы уже использовали обе подсказки на сегодня.\n"
                    "Новые подсказки будут доступны завтра в 00:00"
                )
            }
        
        # Маппинг сложности
        difficulty_emoji = {
            "easy": "🟢 Легкая",
            "medium": "🟡 Средняя",
            "hard": "🔴 Сложная"
        }
        
        # Формируем текст подсказки
        if hints_used == 0:
            # Первая подсказка - базовая информация
            await self.increment_daily_hint(user_id)
            
            return {
                "success": True,
                "hint_number": 1,
                "text": (
                    f"💡 <b>Подсказка дня (1/2)</b>\n\n"
                    f"<b>Длина слова:</b> {len(gene.name)} букв(ы)\n"
                    f"<b>Сложность:</b> {difficulty_emoji.get(gene.difficulty, gene.difficulty)}\n\n"
                    f"💡 <i>Осталась ещё 1 подсказка</i>"
                )
            }
        else:
            # Вторая подсказка - функция гена
            await self.increment_daily_hint(user_id)
            
            return {
                "success": True,
                "hint_number": 2,
                "text": (
                    f"💡 <b>Подсказка дня (2/2)</b>\n\n"
                    f"<b>Длина слова:</b> {len(gene.name)} букв(ы)\n"
                    f"<b>Сложность:</b> {difficulty_emoji.get(gene.difficulty, gene.difficulty)}\n\n"
                    f"<b>Что он делает:</b>\n{gene.hint}\n\n"
                    f"💪 Используйте эту информацию в игре!\n\n"
                    f"⚠️ <i>Это была последняя подсказка на сегодня</i>"
                )
            }