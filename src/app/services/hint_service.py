"""
Сервис подсказок.

Исправлен баг: ранее db.scalar(select(GameSession)...) мог вернуть завершённую
игру с ДРУГИМ геном (не геном дня). Теперь явно фильтруем по gene_id.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from ..db.models.game import GameSession
from ..utils.time_helpers import get_seconds_until_midnight, get_today_date, get_today_str
from .gene_of_day_service import GeneOfDayService

_DIFFICULTY_EMOJI = {
    "easy": "🟢 Лёгкая",
    "medium": "🟡 Средняя",
    "hard": "🔴 Сложная",
}


class HintService:
    """Управление дневными подсказками (лимит 2 шт./день, бесплатно)."""

    MAX_DAILY_HINTS = 2

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis
        self._gene_of_day = GeneOfDayService(db, redis)

    def _hint_key(self, user_id: int) -> str:
        return f"user:{user_id}:daily_hints:{get_today_str()}"

    async def get_daily_hint_count(self, user_id: int) -> int:
        count = await self.redis.get(self._hint_key(user_id))
        return int(count) if count else 0

    async def _increment_daily_hint(self, user_id: int) -> None:
        key = self._hint_key(user_id)
        current = await self.get_daily_hint_count(user_id)
        await self.redis.set(key, current + 1, ex=get_seconds_until_midnight())

    async def show_hint(self, user_id: int, hint_type: str = "daily") -> dict:
        """
        Показать подсказку дня (бесплатную).

        Returns dict:
            {"success": True, "text": "...", "hint_number": 1|2}
            {"success": False, "message": "..."}
        """
        gene = await self._gene_of_day.get()
        hints_used = await self.get_daily_hint_count(user_id)

        # ИСПРАВЛЕНО: проверяем завершение именно игры с геном дня
        finished_game = await self.db.scalar(
            select(GameSession).where(
                GameSession.user_id == user_id,
                GameSession.gene_id == gene.id,  # ← только ген дня!
                GameSession.is_finished == True,
                func.date(GameSession.started_at) == get_today_date(),
            )
        )
        if finished_game:
            outcome = "угадали слово" if finished_game.is_won else "исчерпали все попытки"
            return {
                "success": False,
                "error": "game_finished",
                "message": (
                    f"🔒 <b>Подсказки недоступны</b>\n\n"
                    f"Вы уже завершили сегодняшнюю игру — вы {outcome}.\n"
                    f"Новая игра и подсказки будут доступны завтра в 00:00 🌙"
                ),
            }

        if hints_used >= self.MAX_DAILY_HINTS:
            return {
                "success": False,
                "error": "daily_limit",
                "message": (
                    "💡 <b>Подсказки дня исчерпаны</b>\n\n"
                    "Вы уже использовали обе подсказки на сегодня.\n"
                    "Новые подсказки будут доступны завтра в 00:00"
                ),
            }

        difficulty = _DIFFICULTY_EMOJI.get(gene.difficulty, gene.difficulty)
        await self._increment_daily_hint(user_id)

        if hints_used == 0:
            return {
                "success": True,
                "hint_number": 1,
                "text": (
                    f"💡 <b>Подсказка дня (1/2)</b>\n\n"
                    f"<b>Длина слова:</b> {len(gene.name)} букв(ы)\n"
                    f"<b>Сложность:</b> {difficulty}\n\n"
                    f"💡 <i>Осталась ещё 1 подсказка</i>"
                ),
            }

        return {
            "success": True,
            "hint_number": 2,
            "text": (
                f"💡 <b>Подсказка дня (2/2)</b>\n\n"
                f"<b>Длина слова:</b> {len(gene.name)} букв(ы)\n"
                f"<b>Сложность:</b> {difficulty}\n\n"
                f"<b>Что он делает:</b>\n{gene.hint}\n\n"
                f"💪 Используйте эту информацию в игре!\n\n"
                f"⚠️ <i>Это была последняя подсказка на сегодня</i>"
            ),
        }