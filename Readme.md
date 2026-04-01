# 🧬 Genetic Wordle Bot - Генетический Wordle MyGenetics

Telegram-бот для изучения генов через игру в стиле Wordle.

## 📋 Описание

Игра, где пользователи угадывают названия генов из отчета MyExpert за 6 попыток. После каждой попытки буквы окрашиваются:
- 🟨 **Желтый** - буква на правильном месте
- ⬜ **Белый** - буква есть, но не на месте
- ⬛ **Серый** - буквы нет в слове

### Особенности:
- ⚡ Система энергии (6 единиц в день)
- 💡 Подсказки о функции генов
- 🏆 Система достижений
- 🎁 Призы за победы
- 📊 Статистика игроков
- 🔧 Админ-панель через Telegram и REST API

## 🛠️ Стек технологий

- **Backend**: Python 3.12, FastAPI, Aiogram 3
- **БД**: PostgreSQL 16, Redis 7
- **ORM**: SQLAlchemy 2.0 (async)
- **Dependency Management**: uv
- **Контейнеризация**: Docker, Docker Compose
- **Task Runner**: Makefile

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.12+ (для локальной разработки)
- uv
- make

### Установка зависимостей

```bash
make install
```

### Основные команды

```bash
make docker-up
make migrate
make db-init
make run-api
# bot в отдельном терминале
make run-bot
```

### Проверки

```bash
make lint
make test
```
