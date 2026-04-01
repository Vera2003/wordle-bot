from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect


@pytest.mark.e2e
@pytest.mark.smoke
def test_alembic_upgrade_downgrade_upgrade(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    database_path = tmp_path / "alembic_smoke.db"
    config_path = tmp_path / "alembic.ini"
    config_path.write_text(
        (repo_root / "alembic.ini")
        .read_text()
        .replace(
            "sqlalchemy.url = driver://user:pass@localhost/dbname",
            f"sqlalchemy.url = sqlite+aiosqlite:///{database_path}",
        )
    )

    subprocess.run(
        ["uv", "run", "alembic", "-c", str(config_path), "upgrade", "head"],
        cwd=repo_root,
        check=True,
    )
    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    assert "alembic_version" in inspector.get_table_names()
    engine.dispose()

    subprocess.run(
        ["uv", "run", "alembic", "-c", str(config_path), "downgrade", "base"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        ["uv", "run", "alembic", "-c", str(config_path), "upgrade", "head"],
        cwd=repo_root,
        check=True,
    )

    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    assert "users" in inspector.get_table_names()
    engine.dispose()
