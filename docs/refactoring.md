# Refactoring Notes

This repository was migrated from the legacy flat layout to a layered structure based on the requirements in the root `REFACTORING.md`.

## What was standardized

- `uv` is the package manager and lockfile source of truth
- `Makefile` is the canonical entrypoint for local and CI commands
- DTO contracts live in `src/application` on Pydantic v2
- Alembic targets the current infrastructure metadata
- Tests are organized under `tests/unit`, `tests/integration`, and `tests/e2e`

## Remaining maintenance rules

- keep ORM usage inside `src/infrastructure`
- keep framework-specific code inside `src/interfaces` and `src/bootstrap`
- prefer repository ports and application handlers over ad hoc DB access
- update this document together with any future structural changes
