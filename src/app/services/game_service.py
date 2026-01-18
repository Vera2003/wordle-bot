from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..db.models.user import User
from ..db.models.gene import Gene
from ..db.models.game import GameSession, GameAttempt
from ..schemas.game import LetterStatus, AttemptResult


class GameService:
    """Сервис игровой логики Wordle"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def check_guess(self, target: str, guess: str) -> List[Dict[str, str]]:
        """
        Проверяет попытку угадывания слова.
        
        Возвращает список статусов букв:
        - correct: буква на правильном месте (зеленый/желтый)
        - present: буква есть, но не на месте (белый)
        - absent: буквы нет в слове (серый)
        """
        target = target.upper()
        guess = guess.upper()
        result = []
        target_chars = list(target)
        
        # Первый проход - отмечаем правильные позиции
        for i, char in enumerate(guess):
            if char == target[i]:
                result.append({"letter": char, "status": "correct"})
                target_chars[i] = None  # Помечаем как использованную
            else:
                result.append({"letter": char, "status": "unknown"})
        
        # Второй проход - проверяем присутствие букв
        for i, item in enumerate(result):
            if item["status"] == "unknown":
                char = item["letter"]
                if char in target_chars:
                    item["status"] = "present"
                    target_chars[target_chars.index(char)] = None
                else:
                    item["status"] = "absent"
        
        return result
    
    async def get_random_gene(self) -> Optional[Gene]:
        """Получает случайный активный ген"""
        query = select(Gene).where(Gene.is_active == True)
        result = await self.db.execute(query)
        genes = result.scalars().all()
        
        if not genes:
            return None
        
        return random.choice(genes)
    
    async def start_game(self, user_id: int, gene_id: Optional[int] = None) -> GameSession:
        """
        Начинает новую игру.
        
        Args:
            user_id: ID пользователя
            gene_id: ID гена (если None, выбирается случайный)
        """
        # Проверяем незавершенные игры
        active_game = await self.get_active_game(user_id)
        if active_game:
            return active_game
        
        # Выбираем ген
        if gene_id is None:
            gene = await self.get_random_gene()
            if not gene:
                raise ValueError("Нет доступных генов")
            gene_id = gene.id
        
        # Создаем новую сессию
        session = GameSession(
            user_id=user_id,
            gene_id=gene_id,
            attempts=0,
            max_attempts=6,
            is_won=False,
            is_finished=False,
            hint_used=False
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return session
    
    async def get_active_game(self, user_id: int) -> Optional[GameSession]:
        """Получает активную игру пользователя"""
        query = (
            select(GameSession)
            .where(
                GameSession.user_id == user_id,
                GameSession.is_finished == False
            )
            .order_by(GameSession.started_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def make_attempt(
        self, 
        session_id: int, 
        guess: str
    ) -> AttemptResult:
        """
        Обрабатывает попытку угадывания.
        
        Returns:
            AttemptResult с результатами попытки
        """
        # Получаем сессию с загрузкой гена
        query = (
            select(GameSession)
            .where(GameSession.id == session_id)
            .options(selectinload(GameSession.gene))
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError("Игровая сессия не найдена")
        
        if session.is_finished:
            raise ValueError("Игра уже завершена")
        
        # Проверяем попытку
        target_word = session.gene.name
        guess = guess.upper()
        
        # Валидация
        if len(guess) != len(target_word):
            raise ValueError(f"Слово должно быть {len(target_word)} букв")
        
        # Проверяем угадывание
        check_result = self.check_guess(target_word, guess)
        
        # Увеличиваем счетчик попыток
        session.attempts += 1
        
        # Сохраняем попытку
        attempt = GameAttempt(
            session_id=session.id,
            attempt_number=session.attempts,
            guess_word=guess,
            result=check_result
        )
        self.db.add(attempt)
        
        # Проверяем победу
        is_correct = all(item["status"] == "correct" for item in check_result)
        
        if is_correct:
            session.is_won = True
            session.is_finished = True
            session.finished_at = datetime.utcnow()
            
            # Начисляем очки (больше за меньшее кол-во попыток)
            points = max(10, 60 - (session.attempts * 10))
            session.points_earned = points
            
            # Обновляем очки пользователя
            user_query = select(User).where(User.id == session.user_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one()
            user.total_points += points
        
        # Проверяем проигрыш
        elif session.attempts >= session.max_attempts:
            session.is_finished = True
            session.finished_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(session)
        
        return AttemptResult(
            attempt_number=session.attempts,
            guess=guess,
            result=check_result,
            is_correct=is_correct,
            is_game_over=session.is_finished,
            is_won=session.is_won,
            attempts_left=session.max_attempts - session.attempts,
            points_earned=session.points_earned if session.is_won else 0
        )
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Получает статистику пользователя"""
        # Всего игр
        total_games_query = select(func.count(GameSession.id)).where(
            GameSession.user_id == user_id,
            GameSession.is_finished == True
        )
        total_games = await self.db.scalar(total_games_query)
        
        # Выигранных игр
        won_games_query = select(func.count(GameSession.id)).where(
            GameSession.user_id == user_id,
            GameSession.is_won == True
        )
        won_games = await self.db.scalar(won_games_query)
        
        # Получаем пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        win_rate = (won_games / total_games * 100) if total_games > 0 else 0
        
        return {
            "total_games": total_games or 0,
            "won_games": won_games or 0,
            "lost_games": (total_games or 0) - (won_games or 0),
            "win_rate": round(win_rate, 1),
            "total_points": user.total_points if user else 0
        }
