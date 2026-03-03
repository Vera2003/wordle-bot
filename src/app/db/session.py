from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI-зависимость для получения сессии БД.

    Сессия берётся из app.state.db_session_maker, который
    инициализируется один раз в lifespan (main.py).
    """
    session_maker = request.app.state.db_session_maker
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()