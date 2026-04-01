"""API security helpers."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.infrastructure.config.settings import get_settings

API_KEY_HEADER = APIKeyHeader(name="X-Admin-API-Key", auto_error=True)


async def require_admin_api_key(api_key: str = Security(API_KEY_HEADER)) -> None:
    """Validate admin API key for protected endpoints."""
    settings = get_settings()
    if api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
