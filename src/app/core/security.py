from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.app.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-Admin-API-Key", auto_error=True)

async def require_admin_api_key(api_key: str = Security(API_KEY_HEADER)) -> None:
    if api_key != settings.admin_api_key:   # новая переменная в Settings
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")