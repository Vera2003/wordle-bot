from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Telegram Bot
    bot_token: str = Field(..., description="Telegram Bot Token")
    admin_ids: list[int] = Field(default_factory=list)
    
    # Webhook
    use_webhook: bool = Field(default=False)
    webhook_domain: str = Field(default="")
    webhook_path: str = Field(default="/webhook/bot")
    webhook_secret: str = Field(default="")
    
    # Application
    environment: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    
    # PostgreSQL
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="genetic_wordle")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(..., description="PostgreSQL password")
    
    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_db: int = Field(default=0)
    
    # Game settings
    max_attempts: int = Field(default=6)
    daily_energy: int = Field(default=5)
    energy_per_attempt: int = Field(default=1)
    energy_per_hint: int = Field(default=2)
    bonus_energy: int = Field(default=3)
    
    @property
    def database_url(self) -> str:
        """URL для подключения к PostgreSQL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """URL для подключения к Redis"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def webhook_url(self) -> str:
        """Полный URL для webhook"""
        return f"{self.webhook_domain}{self.webhook_path}"
    
    @field_validator("webhook_domain")
    @classmethod
    def validate_webhook_domain(cls, v):
        """Проверка домена для webhook"""
        if v and not v.startswith("https://"):
            raise ValueError("Webhook домен должен начинаться с https://")
        return v.rstrip("/") if v else ""


settings = Settings()