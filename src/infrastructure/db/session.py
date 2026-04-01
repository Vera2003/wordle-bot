"""Database session dependency for FastAPI."""

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database session.

    Session is retrieved from app.state.db_session_maker, which is
    initialized once in lifespan.
    """
    session_maker = request.app.state.db_session_maker
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
