"""API bootstrap entrypoint."""

from __future__ import annotations

import uvicorn

from src.interfaces.main import create_app

app = create_app()


def main() -> None:
    """Run the FastAPI application."""
    uvicorn.run(
        "src.bootstrap.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
