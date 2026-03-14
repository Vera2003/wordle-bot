# Правила рефакторинга

## Цель

Перевести проект на DDD + Clean Architecture, стандартизировать все входы/выходы через DTO на Pydantic v2, выстроить тестовую пирамиду, заменить `Poetry` на `uv`, сделать `Makefile` единой точкой запуска локальных и CI-команд.

---

## 1. Архитектурные правила

### 1.1. Базовая модель

- Архитектура: `DDD + Clean Architecture`.
- Бизнес-правила не зависят от `FastAPI`, `Aiogram`, `SQLAlchemy`, `Redis`, `OpenAI`, `Telegram`.
- Внешние фреймворки и I/O находятся только во внешних слоях.
- Каждый bounded context изолирован: `game`, `gene`, `user`, `stats`, `prize`, `achievement`, `llm`.

### 1.2. Зависимости между слоями

Разрешенное направление зависимостей:

`interfaces -> application -> domain`

`infrastructure -> domain`

`infrastructure -> application`

Запрещено:

- `domain -> application|infrastructure|interfaces`
- `application -> interfaces`
- прямой доступ хендлеров/роутеров к ORM
- вызов SQLAlchemy-моделей из use case напрямую
- передача `dict`, `Any`, сырых ORM-объектов между слоями

### 1.3. Ответственность слоев

#### `domain/`

- сущности
- value objects
- доменные сервисы
- доменные события
- repository interfaces
- инварианты и бизнес-правила
- доменные ошибки

В домене нельзя:

- импортировать `FastAPI`, `Aiogram`, `SQLAlchemy`, `Redis`, `OpenAI`
- знать о HTTP, Telegram update, ORM schema, JSON response

#### `application/`

- use cases / command handlers / query handlers
- DTO входа и выхода
- orchestration между domain и infrastructure ports
- unit of work interfaces
- policies для транзакций, idempotency, retries на уровне сценария

В application нельзя:

- писать SQL
- работать с Telegram/HTTP напрямую
- сериализовать ответы вручную

#### `infrastructure/`

- SQLAlchemy models
- реализации repository interfaces
- alembic migrations
- Redis adapters
- OpenAI/LLM adapters
- gateway clients
- мапперы ORM <-> domain/application DTO

#### `interfaces/`

- FastAPI routers
- Telegram handlers
- dependency injection wiring
- request/response mapping
- auth entrypoints
- webhook/polling bootstrap

Задача интерфейсов: принять вход, собрать DTO, вызвать use case, отдать DTO-ответ.

---

## 2. DTO и Pydantic v2

### 2.1. Обязательные правила

- Все контракты между слоями — DTO на `Pydantic v2`.
- Использовать только `BaseModel`, `RootModel`, `ConfigDict`, `Field`, `model_validate()`, `model_dump()`.
- Не использовать `.dict()`, `.json()`, `parse_obj()` и legacy API v1.
- Не передавать между слоями `dict` вместо typed DTO.
- Каждый use case принимает `Input DTO` и возвращает `Output DTO`.
- Каждый adapter преобразует внешние данные в DTO на границе.

### 2.2. Где какие DTO живут

- `application/common/dto.py` — базовые DTO, pagination, ids, audit metadata
- `application/<context>/commands/*.py` — input DTO команд
- `application/<context>/queries/*.py` — input DTO запросов
- `application/<context>/dto.py` — output/read DTO
- `interfaces/api/schemas/` не нужны как отдельный слой, если API использует application DTO напрямую
- `infrastructure/db/mappers/` отвечают за преобразование ORM в DTO/domain objects

### 2.3. Формат DTO

- `frozen=True` для immutable DTO, где нет причины менять состояние
- явные типы, без неограниченного `Any`
- алиасы только на внешней границе
- `model_config = ConfigDict(extra="forbid")` для request DTO
- отдельные DTO для `create`, `update`, `read`, `list item`, `details`
- DTO не совмещаются с ORM моделями

---

## 3. Кодстайл рефакторинга

- Один файл — одна четкая ответственность.
- Не держать бизнес-логику в `routers`, `handlers`, `middleware`, `models` ORM.
- `services/` в текущем виде расщепить:
	- доменные сервисы -> `domain/`
	- use cases -> `application/`
	- интеграционные клиенты -> `infrastructure/`
- Все зависимости внедрять через интерфейсы/ports.
- Общие утилиты допустимы только если они не скрывают бизнес-правила.
- Магические строки/числа вынести в value objects, enums или config DTO.
- Асинхронность остается на уровне adapters/use cases, не размазывается по всему коду без необходимости.

---

## 4. Тестирование: пирамида

### 4.1. Правило распределения

Тестовая пирамида:

- `70%` unit
- `20%` integration
- `10%` e2e / smoke

### 4.2. Слои тестов

#### Unit

Покрывают:

- domain entities/value objects
- domain services
- application use cases
- policies, validators, mappers без I/O

Требования:

- без БД
- без сети
- без Redis
- без Telegram/OpenAI
- через fake/stub/mock ports

#### Integration

Покрывают:

- SQLAlchemy repositories
- Alembic migrations
- Redis adapters
- FastAPI dependency wiring
- OpenAI/LLM adapter contracts

Требования:

- реальные интеграции в docker test environment
- отдельные фикстуры на Postgres/Redis
- проверка транзакций, индексов, ограничений, сериализации

#### E2E / Smoke

Покрывают:

- основной пользовательский сценарий игры
- выдачу подсказки
- начисление энергии
- получение статистики
- webhook/API happy path

### 4.3. Организация тестов

- Тесты зеркалят production-структуру.
- Для каждого use case обязателен unit-тест набора success/failure сценариев.
- Для каждого repository adapter обязателен integration-тест.
- Для каждой миграции обязателен smoke-проход `upgrade -> downgrade -> upgrade`.

---

## 5. Makefile

`Makefile` становится канонической точкой запуска. `Taskfile.yaml` удаляется после достижения паритета.

Минимальный набор target'ов:

- `make install` — `uv sync --all-groups`
- `make run-api` — запуск FastAPI
- `make run-bot` — запуск Telegram bot
- `make docker-up`
- `make docker-down`
- `make lint`
- `make test`
- `make test-unit`
- `make test-integration`
- `make migrate`
- `make revision message="..."`
- `make all` — полный прогон `lint + test`

Правила:

- внутри `Makefile` только короткие, стабильные команды
- все команды выполняются через `uv run ...`
- одинаковые target'ы используются локально и в CI
- `all` не должен иметь скрытых побочных эффектов кроме проверок

---

## 6. Миграция на uv

### 6.1. Целевое состояние

- dependency manager: `uv`
- lockfile: `uv.lock`
- `Poetry` удален из проекта
- `poetry.lock` удален
- `pyproject.toml` переведен на PEP 621 (`[project]` + dependency groups)

### 6.2. Правила миграции

- Перенести зависимости из `[tool.poetry.*]` в `[project]` и dependency groups.
- Dev-зависимости разнести минимум по группам:
	- `lint`
	- `test`
	- `dev`
- После переноса зафиксировать `uv.lock`.
- Любой запуск в документации, CI и `Makefile` должен идти через:
	- `uv sync`
	- `uv run`
	- `uv lock --check`

### 6.3. Команды, которые должны стать стандартом

- `uv sync --all-groups`
- `uv run pytest`
- `uv run alembic upgrade head`
- `uv run python -m ...`
- `uv lock --check`

---

## 7. Целевая структура проекта после рефакторинга

```text
.
├── Makefile
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── alembic/
├── docs/
│   ├── architecture.md
│   └── refactoring.md
├── scripts/
├── src/
│   ├── bootstrap/
│   │   ├── api.py
│   │   ├── bot.py
│   │   └── container.py
│   ├── domain/
│   │   ├── shared/
│   │   │   ├── errors.py
│   │   │   ├── events.py
│   │   │   └── types.py
│   │   ├── game/
│   │   │   ├── entities.py
│   │   │   ├── value_objects.py
│   │   │   ├── services.py
│   │   │   ├── repositories.py
│   │   │   └── errors.py
│   │   ├── gene/
│   │   ├── user/
│   │   ├── stats/
│   │   ├── prize/
│   │   ├── achievement/
│   │   └── llm/
│   ├── application/
│   │   ├── common/
│   │   │   ├── dto.py
│   │   │   ├── interfaces.py
│   │   │   └── uow.py
│   │   ├── game/
│   │   │   ├── commands/
│   │   │   │   ├── start_game.py
│   │   │   │   ├── submit_guess.py
│   │   │   │   └── use_case.py
│   │   │   ├── queries/
│   │   │   │   ├── get_game_state.py
│   │   │   │   └── use_case.py
│   │   │   └── dto.py
│   │   ├── gene/
│   │   ├── user/
│   │   ├── stats/
│   │   ├── prize/
│   │   ├── achievement/
│   │   └── llm/
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── mappers/
│   │   │   ├── session.py
│   │   │   └── uow.py
│   │   ├── cache/
│   │   │   └── redis/
│   │   ├── llm/
│   │   │   └── openai/
│   │   ├── telemetry/
│   │   └── config/
│   ├── interfaces/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   ├── exception_handlers.py
│   │   │   └── v1/
│   │   │       ├── game.py
│   │   │       ├── genes.py
│   │   │       ├── users.py
│   │   │       ├── prizes.py
│   │   │       ├── stats.py
│   │   │       └── llm.py
│   │   └── bot/
│   │       ├── handlers/
│   │       ├── middleware/
│   │       ├── keyboards/
│   │       └── presenters/
│   └── main.py
└── tests/
		├── unit/
		│   ├── domain/
		│   └── application/
		├── integration/
		│   ├── db/
		│   ├── api/
		│   ├── redis/
		│   └── llm/
		└── e2e/
				├── api/
				└── bot/
```

---

## 8. Карта переноса текущего кода

### Перенести

- `src/services/*` -> `domain/*` и `application/*`
- `src/db/models/*` -> `infrastructure/db/models/*`
- `src/app/api/*` -> `interfaces/api/*`
- `src/app/bot/*` -> `interfaces/bot/*`
- `src/schemas/*` -> `application/*/dto.py` или `application/common/dto.py`
- `src/core/config.py` -> `infrastructure/config/`
- `src/core/security.py` -> `interfaces/api/` или `application/common/`, по реальной ответственности

### Удалить как архитектурный слой

- `src/services` в текущем плоском виде
- `src/schemas` как свалку DTO без контекста
- смешение HTTP/Telegram/DB-логики в одном модуле

---

## 9. Definition of Done для рефакторинга

Рефакторинг считается завершенным, когда:

- проект запускается через `uv`
- есть `Makefile` с обязательными target'ами
- нет зависимости от `Poetry`
- use cases отделены от adapters
- все входы/выходы типизированы DTO на Pydantic v2
- ORM используется только в `infrastructure`
- тесты разложены по пирамиде
- текущие бизнес-сценарии покрыты unit + integration + smoke
- документация отражает новую структуру, а старая удалена или переписана
