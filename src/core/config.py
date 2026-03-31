"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Telegram Bot
    bot_token: str = Field(default="", description="Telegram Bot Token")
    admin_ids: list[int] = Field(default_factory=list)
    admin_api_key: str = Field(default="", description="Secret key for REST admin API")

    # Webhook
    use_webhook: bool = Field(default=False)
    webhook_domain: str = Field(default="")
    webhook_path: str = Field(default="/webhook/bot")
    webhook_secret: str = Field(default="")

    # Application
    environment: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    allowed_origins: List[str] = Field(default=[])
    CORS_ORIGINS: List[str] = Field(default=[])

    # PostgreSQL
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="genetic_wordle")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="", description="PostgreSQL password")

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_db: int = Field(default=0)

    # Game settings
    max_attempts: int = Field(default=6)
    daily_energy: int = Field(default=6)
    energy_per_attempt: int = Field(default=1)
    energy_per_hint: int = Field(default=2)
    bonus_energy: int = Field(default=3)

    # ProxyAPI (proxy to OpenAI, https://proxyapi.ru)
    proxyapi_key: str = Field(default="", description="API-key from proxyapi.ru")
    proxyapi_model: str = Field(default="gpt-4o-mini", description="Model: gpt-4o-mini, gpt-4o, gpt-4-turbo")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.proxyapi_key)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_domain}{self.webhook_path}"

    @field_validator("webhook_domain")
    @classmethod
    def validate_webhook_domain(cls, v: str) -> str:
        if v and not v.startswith("https://"):
            raise ValueError("Webhook domain must start with https://")
        return v.rstrip("/") if v else ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings.

    Use this function everywhere instead of directly importing `settings`:

        # ✅ In FastAPI dependencies:
        def my_route(settings: Settings = Depends(get_settings)):
            ...

        # ✅ In services and scripts:
        from .config import get_settings
        settings = get_settings()

        # ✅ In tests — easily replaced:
        get_settings.cache_clear()
        monkeypatch.setenv("POSTGRES_DB", "test_db")
        settings = get_settings()  # returns new object with test values

    Cache is cleared via get_settings.cache_clear().
    """
    return Settings()
