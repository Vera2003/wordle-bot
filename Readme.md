# 🧬 Genetic Wordle Bot - Генетический Wordle MyGenetics

Telegram-бот для изучения генов через игру в стиле Wordle.

## 📋 Описание

Игра, где пользователи угадывают названия генов из отчета MyExpert за 6 попыток. После каждой попытки буквы окрашиваются:
- 🟨 **Желтый** - буква на правильном месте
- ⬜ **Белый** - буква есть, но не на месте
- ⬛ **Серый** - буквы нет в слове

### Особенности:
- ⚡ Система энергии (5 единиц в день)
- 💡 Подсказки о функции генов
- 🏆 Система достижений
- 🎁 Призы за победы
- 📊 Статистика игроков
- 🔧 Админ-панель через Telegram и REST API

## 🛠️ Стек технологий

- **Backend**: Python 3.12, FastAPI, Aiogram 3
- **БД**: PostgreSQL 16, Redis 7
- **ORM**: SQLAlchemy 2.0 (async)
- **Dependency Management**: Poetry
- **Контейнеризация**: Docker, Docker Compose
- **Task Runner**: Taskfile

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.12+ (для локальной разработки)
- Poetry (опционально)
- Task (опционально, но рекомендуется)

### Установка Task

```bash
# macOS
brew install go-task

# Linux
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

# Windows (Chocolatey)
choco install go-task
