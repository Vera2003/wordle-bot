from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context # type: ignore[attr-defined]
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config

# Добавляем путь к приложению
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.core.config import get_settings
from src.app.db.base import Base

# Импортируем все модели
from src.app.db.models.user import User
from src.app.db.models.gene import Gene
from src.app.db.models.game import GameSession, GameAttempt
from src.app.db.models.achievements import AchievementType, UserAchievement
from src.app.db.models.prize import PrizeType, UserPrize
from src.app.db.models.llm_log import LLMLog

# Конфигурация Alembic
config = context.config

# Устанавливаем URL базы данных
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Настраиваем логирование
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные для автогенерации миграций
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Миграции в offline режиме"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Миграции в online режиме (async)"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в online режиме"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
