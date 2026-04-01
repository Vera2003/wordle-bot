# Architecture

## Overview

The project follows `DDD + Clean Architecture` with the dependency flow:

`interfaces -> application -> domain`

Infrastructure adapters implement persistence and external integrations without leaking ORM models into the higher layers.

## Current layout

- `src/domain` — entities, value objects, repository ports, domain services and errors
- `src/application` — command/query handlers and DTO contracts on Pydantic v2
- `src/infrastructure` — SQLAlchemy models, repository implementations, config, LLM adapter, telemetry
- `src/interfaces` — FastAPI routes, Telegram handlers, middleware and API security
- `src/bootstrap` — runnable entrypoints for API and bot
- `tests` — unit, integration and e2e/smoke checks

## Runtime boundaries

- FastAPI and Aiogram wiring stays in `src/interfaces`
- SQLAlchemy ORM stays in `src/infrastructure/db`
- Application use cases receive typed DTOs and domain ports
- Telegram-facing compatibility helpers in `src/interfaces/bot/legacy_facade.py` use repositories and use cases, not ORM models
