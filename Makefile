.PHONY: help install run-api run-bot docker-up docker-down lint test test-unit test-integration test-smoke db-init migrate revision all

# Переменные
PYTHON := uv run python
PYTEST := uv run pytest
VENV_DIR := .venv

help: ## Показать помощь со всеми доступными командами
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить все зависимости (основные + dev)
	uv sync --all-groups

run-api: ## Запустить FastAPI сервер (http://localhost:8000)
	$(PYTHON) -m src.bootstrap.api

run-bot: ## Запустить Telegram бота в polling режиме
	$(PYTHON) -m src.bootstrap.bot

docker-up: ## Поднять Docker контейнеры (Postgres, Redis)
	docker-compose -f ci-cd-files/docker-compose.yml up -d

docker-down: ## Остановить Docker контейнеры
	docker-compose -f ci-cd-files/docker-compose.yml down

lint: ## Запустить linters (flake8, isort, black)
	$(PYTHON) -m black src tests --check
	$(PYTHON) -m isort src tests --check-only
	$(PYTHON) -m flake8 src tests
	$(PYTHON) -m mypy src --strict --ignore-missing-imports

lint-fix: ## Автоматически исправить стиль кода (black, isort)
	$(PYTHON) -m isort src tests
	$(PYTHON) -m black src tests

test: ## Запустить все тесты
	$(PYTEST) tests -v

test-unit: ## Запустить только unit тесты
	$(PYTEST) tests/unit -v

test-integration: ## Запустить только integration тесты
	$(PYTEST) tests/integration -v

test-smoke: ## Запустить smoke/e2e проверки
	$(PYTEST) tests/e2e -v

test-cov: ## Запустить тесты с отчетом покрытия
	$(PYTEST) tests --cov=src --cov-report=html --cov-report=term

db-init: ## Инициализировать базовые данные (гены, достижения, призы)
	$(PYTHON) scripts/init_genes.py

migrate: ## Применить миграции Alembic (upgrade head)
	$(PYTHON) -m alembic upgrade head

migrate-down: ## Откатить последнюю миграцию
	$(PYTHON) -m alembic downgrade -1

revision: ## Создать новую миграцию (используй: make revision message="descriptive name")
	@if [ -z "$(message)" ]; then \
		echo "❌ Ошибка: укажи имя миграции. Пример: make revision message='add_user_table'"; \
		exit 1; \
	fi
	$(PYTHON) -m alembic revision --autogenerate -m "$(message)"

all: lint test ## Запустить полную проверку (lint + test)

clean: ## Очистить кэш и временные файлы
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .venv -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

.DEFAULT_GOAL := help
