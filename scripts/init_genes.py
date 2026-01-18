"""
Скрипт для инициализации БД генами из ТЗ
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from src.app.core.config import settings
from src.app.db.base import Base
from src.app.db.models.gene import Gene
from src.app.db.models.user import User
from src.app.db.models.game import GameSession, GameAttempt
from src.app.db.models.achievement import AchievementType, UserAchievement
from src.app.db.models.prize import PrizeType, UserPrize


# Список генов из ТЗ
GENES_DATA = [
    {
        "name": "TCF7L2",
        "description": "Ген, связанный с риском развития диабета 2 типа. Влияет на выработку инсулина и регуляцию уровня глюкозы в крови.",
        "hint": "Этот ген играет ключевую роль в развитии диабета 2 типа",
        "difficulty": "medium"
    },
    {
        "name": "PPARG",
        "description": "Регулирует метаболизм жиров и углеводов, влияет на чувствительность к инсулину.",
        "hint": "Важен для метаболизма жиров и углеводов",
        "difficulty": "easy"
    },
    {
        "name": "GLUT2",
        "description": "Транспортер глюкозы, важен для регуляции уровня сахара в крови.",
        "hint": "Транспортирует глюкозу в клетках",
        "difficulty": "easy"
    },
    {
        "name": "KCNJ11",
        "description": "Влияет на секрецию инсулина поджелудочной железой.",
        "hint": "Связан с работой поджелудочной железы и выработкой инсулина",
        "difficulty": "hard"
    },
    {
        "name": "ADRB2",
        "description": "Бета-2 адренорецептор, влияет на метаболизм жиров и работу сердечно-сосудистой системы.",
        "hint": "Регулирует метаболизм жиров и работу сердца",
        "difficulty": "easy"
    },
    {
        "name": "AGER",
        "description": "Рецептор конечных продуктов гликирования, связан с воспалением и старением.",
        "hint": "Влияет на процессы воспаления и старения организма",
        "difficulty": "medium"
    },
    {
        "name": "APOE",
        "description": "Аполипопротеин E, влияет на метаболизм холестерина и риск болезни Альцгеймера.",
        "hint": "Важен для обмена холестерина и здоровья мозга",
        "difficulty": "medium"
    },
    {
        "name": "CETP",
        "description": "Белок переноса эфиров холестерина, влияет на уровень холестерина ЛПВП.",
        "hint": "Регулирует уровень 'хорошего' холестерина",
        "difficulty": "medium"
    },
    {
        "name": "FADS1",
        "description": "Участвует в метаболизме жирных кислот омега-3 и омега-6.",
        "hint": "Отвечает за переработку полезных жирных кислот",
        "difficulty": "easy"
    },
    {
        "name": "APOA5",
        "description": "Аполипопротеин A5, регулирует уровень триглицеридов в крови.",
        "hint": "Контролирует уровень триглицеридов",
        "difficulty": "easy"
    },
    {
        "name": "FABP2",
        "description": "Белок, связывающий жирные кислоты, влияет на всасывание жиров в кишечнике.",
        "hint": "Помогает усваивать жиры из пищи",
        "difficulty": "easy"
    },
    {
        "name": "LCT",
        "description": "Ген лактазы, определяет способность переваривать молочный сахар (лактозу).",
        "hint": "Отвечает за переваривание молочных продуктов",
        "difficulty": "easy"
    },
    {
        "name": "BCMO1",
        "description": "Преобразует бета-каротин в витамин А.",
        "hint": "Превращает морковный пигмент в витамин А",
        "difficulty": "easy"
    },
    {
        "name": "VDR",
        "description": "Рецептор витамина D, влияет на усвоение кальция и здоровье костей.",
        "hint": "Помогает организму использовать витамин D",
        "difficulty": "easy"
    },
    {
        "name": "MTHFR",
        "description": "Участвует в метаболизме фолиевой кислоты и гомоцистеина.",
        "hint": "Важен для обмена фолиевой кислоты",
        "difficulty": "easy"
    },
]


async def init_database():
    """Инициализация базы данных"""
    print("🔧 Подключение к базе данных...")
    engine = create_async_engine(settings.database_url, echo=True)
    
    print("📦 Создание таблиц...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Таблицы созданы")
    
    # Создаём сессию
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        print("🧬 Добавление генов...")
        
        for gene_data in GENES_DATA:
            # Проверяем, есть ли уже такой ген
            query = select(Gene).where(Gene.name == gene_data["name"])
            result = await session.execute(query)
            existing = result.scalar_one_or_none()
            
            if not existing:
                gene = Gene(**gene_data)
                session.add(gene)
                print(f"  ✓ Добавлен: {gene_data['name']}")
            else:
                print(f"  ⊙ Уже есть: {gene_data['name']}")
        
        await session.commit()
        print(f"✅ Добавлено {len(GENES_DATA)} генов")
    
    await engine.dispose()
    print("🎉 Инициализация завершена!")


if __name__ == "__main__":
    asyncio.run(init_database())
