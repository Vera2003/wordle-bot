FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

ENV PATH="$POETRY_HOME/bin:$PATH"

# ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc g++ libpq-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry через pip
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

# Копируем pyproject.toml (lock может отсутствовать)
COPY pyproject.toml poetry.lock ./

# Генерируем poetry.lock если его нет
RUN poetry lock --no-update

# ============================================================================
FROM base AS production

# Устанавливаем зависимости
RUN poetry install --only main --no-root --no-interaction

# Копируем код
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Непривилегированный пользователь
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]