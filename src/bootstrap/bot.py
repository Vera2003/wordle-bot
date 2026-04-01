"""Bot bootstrap entrypoint."""

from __future__ import annotations

import asyncio

from src.interfaces.bot.main import main as run_bot


def main() -> None:
    """Run the Telegram bot in polling mode."""
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()