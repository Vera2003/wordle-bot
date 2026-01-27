"""
Скрипт для полной инициализации базы данных
Создаёт таблицы и добавляет начальные данные:
- Гены (15 штук из ТЗ)
- Типы достижений (Серебро, Золото, Платина)
- Типы призов (скидки, бонусы)
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

# Добавляем корень проекта в PYTHONPATH
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from src.app.core.config import settings
from src.app.db.base import Base
from src.app.db.models.gene import Gene
from src.app.db.models.user import User
from src.app.db.models.game import GameSession, GameAttempt
from src.app.db.models.achievements import AchievementType, UserAchievement
from src.app.db.models.prize import PrizeType, UserPrize


# ============================================================================
# ГЕНЫ ИЗ ТЗ (15 ШТУК)
# ============================================================================

GENES_DATA = [
    {
        "name": "TCF7L2",
        "description": "Ген, связанный с риском развития диабета 2 типа. Влияет на выработку инсулина и регуляцию уровня глюкозы в крови. Один из главных генетических факторов развития сахарного диабета.",
        "hint": "Этот ген играет ключевую роль в развитии диабета 2 типа",
        "difficulty": "medium"
    },
    {
        "name": "PPARG",
        "description": "Регулирует метаболизм жиров и углеводов, влияет на чувствительность к инсулину. Играет важную роль в накоплении жировой ткани и энергетическом обмене.",
        "hint": "Важен для метаболизма жиров и углеводов",
        "difficulty": "easy"
    },
    {
        "name": "GLUT2",
        "description": "Транспортер глюкозы, важен для регуляции уровня сахара в крови. Обеспечивает транспорт глюкозы в клетки печени и поджелудочной железы.",
        "hint": "Транспортирует глюкозу в клетках",
        "difficulty": "easy"
    },
    {
        "name": "KCNJ11",
        "description": "Влияет на секрецию инсулина поджелудочной железой. Мутации в этом гене могут приводить к неонатальному диабету или изменению чувствительности к препаратам.",
        "hint": "Связан с работой поджелудочной железы и выработкой инсулина",
        "difficulty": "hard"
    },
    {
        "name": "ADRB2",
        "description": "Бета-2 адренорецептор, влияет на метаболизм жиров и работу сердечно-сосудистой системы. Участвует в регуляции расширения бронхов и расщепления жиров.",
        "hint": "Регулирует метаболизм жиров и работу сердца",
        "difficulty": "easy"
    },
    {
        "name": "AGER",
        "description": "Рецептор конечных продуктов гликирования, связан с воспалением и старением. Его активация участвует в развитии осложнений диабета и возрастных заболеваний.",
        "hint": "Влияет на процессы воспаления и старения организма",
        "difficulty": "medium"
    },
    {
        "name": "APOE",
        "description": "Аполипопротеин E, влияет на метаболизм холестерина и риск болезни Альцгеймера. Разные варианты этого гена определяют риск развития сердечно-сосудистых и нейродегенеративных заболеваний.",
        "hint": "Важен для обмена холестерина и здоровья мозга",
        "difficulty": "medium"
    },
    {
        "name": "CETP",
        "description": "Белок переноса эфиров холестерина, влияет на уровень холестерина ЛПВП (хорошего холестерина). Играет ключевую роль в обратном транспорте холестерина.",
        "hint": "Регулирует уровень 'хорошего' холестерина",
        "difficulty": "medium"
    },
    {
        "name": "FADS1",
        "description": "Участвует в метаболизме жирных кислот омега-3 и омега-6. Кодирует фермент, который превращает растительные омега-кислоты в их активные формы.",
        "hint": "Отвечает за переработку полезных жирных кислот",
        "difficulty": "easy"
    },
    {
        "name": "APOA5",
        "description": "Аполипопротеин A5, регулирует уровень триглицеридов в крови. Низкий уровень этого белка связан с повышенным риском сердечно-сосудистых заболеваний.",
        "hint": "Контролирует уровень триглицеридов",
        "difficulty": "easy"
    },
    {
        "name": "FABP2",
        "description": "Белок, связывающий жирные кислоты, влияет на всасывание жиров в кишечнике. Определяет эффективность усвоения пищевых жиров и может влиять на метаболический синдром.",
        "hint": "Помогает усваивать жиры из пищи",
        "difficulty": "easy"
    },
    {
        "name": "LCT",
        "description": "Ген лактазы, определяет способность переваривать молочный сахар (лактозу). Мутации в этом гене вызывают непереносимость лактозы у взрослых.",
        "hint": "Отвечает за переваривание молочных продуктов",
        "difficulty": "easy"
    },
    {
        "name": "BCMO1",
        "description": "Преобразует бета-каротин (провитамин А) в активный витамин А. Вариации гена влияют на эффективность усвоения витамина А из растительных продуктов.",
        "hint": "Превращает морковный пигмент в витамин А",
        "difficulty": "easy"
    },
    {
        "name": "VDR",
        "description": "Рецептор витамина D, влияет на усвоение кальция и здоровье костей. Также участвует в регуляции иммунной системы и клеточного деления.",
        "hint": "Помогает организму использовать витамин D",
        "difficulty": "easy"
    },
    {
        "name": "MTHFR",
        "description": "Участвует в метаболизме фолиевой кислоты и гомоцистеина. Мутации в этом гене могут повышать риск сердечно-сосудистых заболеваний и осложнений беременности.",
        "hint": "Важен для обмена фолиевой кислоты",
        "difficulty": "easy"
    }
]


# ============================================================================
# ТИПЫ ДОСТИЖЕНИЙ
# ============================================================================

ACHIEVEMENT_TYPES = [
    {
        "name": "silver",
        "title": "🥈 Серебро",
        "description": "Выиграйте 5 игр подряд",
        "requirement": 5,
        "reward_type": "discount",
        "reward_value": "10"  # 10% скидка
    },
    {
        "name": "gold",
        "title": "🥇 Золото",
        "description": "Выиграйте 10 игр",
        "requirement": 10,
        "reward_type": "fast_delivery",
        "reward_value": "true"
    },
    {
        "name": "platinum",
        "title": "💎 Платина",
        "description": "Выиграйте 20 игр",
        "requirement": 20,
        "reward_type": "consultation",
        "reward_value": "true"
    },
    {
        "name": "perfect_game",
        "title": "🎯 Идеальная игра",
        "description": "Угадайте ген с первой попытки",
        "requirement": 1,
        "reward_type": "bonus_energy",
        "reward_value": "5"
    },
    {
        "name": "streak_3",
        "title": "🔥 Серия из 3",
        "description": "Выиграйте 3 игры подряд",
        "requirement": 3,
        "reward_type": "bonus_energy",
        "reward_value": "3"
    },
    {
        "name": "night_owl",
        "title": "🦉 Ночная сова",
        "description": "Играйте после полуночи",
        "requirement": 1,
        "reward_type": "bonus_energy",
        "reward_value": "2"
    },
    {
        "name": "speedrunner",
        "title": "⚡ Спидраннер",
        "description": "Завершите игру за 60 секунд",
        "requirement": 1,
        "reward_type": "bonus_energy",
        "reward_value": "3"
    },
    {
        "name": "gene_master",
        "title": "🧬 Мастер генов",
        "description": "Угадайте все 15 генов хотя бы раз",
        "requirement": 15,
        "reward_type": "special_prize",
        "reward_value": "certificate"
    }
]


# ============================================================================
# ТИПЫ ПРИЗОВ
# ============================================================================

PRIZE_TYPES = [
    {
        "name": "discount_10",
        "title": "Скидка 10%",
        "description": "Скидка 10% на следующий заказ MyExpert",
        "prize_value": "GENE10",
        "is_active": True
    },
    {
        "name": "discount_15",
        "title": "Скидка 15%",
        "description": "Скидка 15% на следующий заказ MyExpert",
        "prize_value": "GENE15",
        "is_active": True
    },
    {
        "name": "discount_20",
        "title": "Скидка 20%",
        "description": "Скидка 20% на следующий заказ MyExpert",
        "prize_value": "GENE20",
        "is_active": True
    },
    {
        "name": "free_delivery",
        "title": "Бесплатная доставка",
        "description": "Ускоренная доставка бесплатно",
        "prize_value": "EXPRESS_FREE",
        "is_active": True
    },
    {
        "name": "consultation",
        "title": "Бонусная консультация",
        "description": "Бесплатная консультация генетика",
        "prize_value": "CONSULT_FREE",
        "is_active": True
    },
    {
        "name": "gift_card_500",
        "title": "Подарочная карта 500₽",
        "description": "Подарочная карта на 500 рублей",
        "prize_value": "GIFT500",
        "is_active": True
    },
    {
        "name": "gift_card_1000",
        "title": "Подарочная карта 1000₽",
        "description": "Подарочная карта на 1000 рублей",
        "prize_value": "GIFT1000",
        "is_active": True
    },
    {
        "name": "certificate",
        "title": "Сертификат мастера генов",
        "description": "Именной сертификат 'Мастер генетики'",
        "prize_value": "MASTER_CERT",
        "is_active": True
    }
]


# ============================================================================
# ФУНКЦИИ ИНИЦИАЛИЗАЦИИ
# ============================================================================

async def init_database():
    """Полная инициализация базы данных"""
    
    print("=" * 70)
    print("🔧 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 70)
    
    # Подключение к БД
    print(f"\n📡 Подключение к PostgreSQL...")
    print(f"   Host: {settings.postgres_host}")
    print(f"   Port: {settings.postgres_port}")
    print(f"   Database: {settings.postgres_db}")
    print(f"   User: {settings.postgres_user}")
    
    engine = create_async_engine(settings.database_url, echo=False)
    
    try:
        # Создание таблиц
        print("\n📦 Создание таблиц...")
        async with engine.begin() as conn:
            # Удаляем старые таблицы
            await conn.run_sync(Base.metadata.drop_all)
            print("   ✓ Старые таблицы удалены")
            
            # Создаём новые таблицы
            await conn.run_sync(Base.metadata.create_all)
            print("   ✓ Новые таблицы созданы")
        
        # Создаём сессию
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        
        async with async_session() as session:
            # ========================================
            # ГЕНЫ
            # ========================================
            print("\n🧬 Добавление генов...")
            genes_added = 0
            
            for gene_data in GENES_DATA:
                # Проверяем, есть ли уже такой ген
                query = select(Gene).where(Gene.name == gene_data["name"])
                result = await session.execute(query)
                existing = result.scalar_one_or_none()
                
                if not existing:
                    gene = Gene(**gene_data, is_active=True)
                    session.add(gene)
                    genes_added += 1
                    print(f"   ✓ {gene_data['name']:8} - {gene_data['difficulty']:6} - {gene_data['description'][:60]}...")
            
            await session.commit()
            print(f"\n   📊 Всего генов добавлено: {genes_added}/{len(GENES_DATA)}")
            
            # ========================================
            # ТИПЫ ДОСТИЖЕНИЙ
            # ========================================
            print("\n🏆 Добавление типов достижений...")
            achievements_added = 0
            
            for achievement_data in ACHIEVEMENT_TYPES:
                query = select(AchievementType).where(
                    AchievementType.name == achievement_data["name"]
                )
                result = await session.execute(query)
                existing = result.scalar_one_or_none()
                
                if not existing:
                    achievement = AchievementType(**achievement_data)
                    session.add(achievement)
                    achievements_added += 1
                    print(f"   ✓ {achievement_data['title']:20} - {achievement_data['description']}")
            
            await session.commit()
            print(f"\n   📊 Всего достижений добавлено: {achievements_added}/{len(ACHIEVEMENT_TYPES)}")
            
            # ========================================
            # ТИПЫ ПРИЗОВ
            # ========================================
            print("\n🎁 Добавление типов призов...")
            prizes_added = 0
            
            for prize_data in PRIZE_TYPES:
                query = select(PrizeType).where(
                    PrizeType.name == prize_data["name"]
                )
                result = await session.execute(query)
                existing = result.scalar_one_or_none()
                
                if not existing:
                    prize = PrizeType(**prize_data)
                    session.add(prize)
                    prizes_added += 1
                    print(f"   ✓ {prize_data['title']:30} - {prize_data['prize_value']}")
            
            await session.commit()
            print(f"\n   📊 Всего призов добавлено: {prizes_added}/{len(PRIZE_TYPES)}")
        
        print("\n" + "=" * 70)
        print("✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 70)
        print(f"\n📈 Статистика:")
        print(f"   • Генов: {len(GENES_DATA)}")
        print(f"   • Достижений: {len(ACHIEVEMENT_TYPES)}")
        print(f"   • Призов: {len(PRIZE_TYPES)}")
        print(f"\n🎮 Бот готов к работе!")
        print()
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await engine.dispose()
    
    return True


# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == "__main__":
    # Запускаем инициализацию
    success = asyncio.run(init_database())
    
    # Код выхода для shell скриптов
    sys.exit(0 if success else 1)
