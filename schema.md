genetic-wordle-bot/
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI приложение (админ-панель)
│   │   │
│   │   ├── bot/                       # Telegram бот
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # Точка входа бота
│   │   │   ├── handlers/             # Обработчики команд/сообщений
│   │   │   │   ├── __init__.py
│   │   │   │   ├── start.py         # /start, главное меню
│   │   │   │   ├── game.py          # Игровой процесс
│   │   │   │   ├── achievements.py  # Достижения
│   │   │   │   └── admin.py         # Админ-команды
│   │   │   ├── keyboards/            # Клавиатуры
│   │   │   │   ├── __init__.py
│   │   │   │   ├── menu.py          # Главное меню
│   │   │   │   └── game.py          # Игровые кнопки
│   │   │   ├── middleware/           # Middleware
│   │   │   │   ├── __init__.py
│   │   │   │   └── throttling.py    # Защита от спама
│   │   │   ├── states/               # FSM состояния
│   │   │   │   ├── __init__.py
│   │   │   │   └── game.py          # Игровые состояния
│   │   │   └── texts/                # Текстовые константы
│   │   │       ├── __init__.py
│   │   │       └── messages.py
│   │   │
│   │   ├── api/                       # FastAPI роуты (админ-панель)
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── genes.py         # CRUD генов
│   │   │   │   ├── hints.py         # Управление подсказками
│   │   │   │   ├── prizes.py        # Управление призами
│   │   │   │   └── stats.py         # Статистика
│   │   │   └── deps.py              # Зависимости API
│   │   │
│   │   ├── core/                      # Ядро приложения
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Конфигурация (Pydantic Settings)
│   │   │   ├── container.py         # DI контейнер
│   │   │   └── security.py          # Авторизация админ-панели
│   │   │
│   │   ├── db/                        # База данных
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base модель SQLAlchemy
│   │   │   ├── session.py           # Сессии БД
│   │   │   ├── models/              # ORM модели
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py          # Пользователи
│   │   │   │   ├── gene.py          # Гены
│   │   │   │   ├── game.py          # Игровые сессии
│   │   │   │   ├── achievement.py   # Достижения
│   │   │   │   └── prize.py         # Призы
│   │   │   └── repositories/        # Репозитории (паттерн Repository)
│   │   │       ├── __init__.py
│   │   │       ├── user.py
│   │   │       ├── gene.py
│   │   │       ├── game.py
│   │   │       └── achievement.py
│   │   │
│   │   ├── services/                  # Бизнес-логика
│   │   │   ├── __init__.py
│   │   │   ├── game_service.py      # Логика игры Wordle
│   │   │   ├── energy_service.py    # Управление энергией
│   │   │   ├── hint_service.py      # Система подсказок
│   │   │   ├── prize_service.py     # Выдача призов
│   │   │   └── achievement_service.py # Система достижений
│   │   │
│   │   ├── schemas/                   # Pydantic схемы
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── gene.py
│   │   │   ├── game.py
│   │   │   └── prize.py
│   │   │
│   │   └── utils/                     # Утилиты
│   │       ├── __init__.py
│   │       ├── redis_client.py      # Redis клиент
│   │       └── validators.py        # Валидаторы (длина слова и т.д.)
│   │
│   └── tests/                         # Тесты
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_game_service.py
│       └── test_energy_service.py
│
├── alembic/                           # Миграции БД
│   ├── versions/
│   └── env.py
│
├── ci-cd-files/                       # Docker и деплой
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose-test.yml
│
├── scripts/                           # Скрипты
│   └── init_genes.py                 # Инициализация БД генами
│
├── .env-example
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini
├── pyproject.toml
├── uv.lock
├── README.md
└── Makefile
