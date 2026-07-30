from enum import Enum
from typing import Optional
from pydantic import PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

    # Core settings
    ENV: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    CREATOR_ID: int  # Telegram ID владельца/разработчика для алертов
    
    # Telegram Bot Settings
    BOT_TOKEN: SecretStr
    USE_WEBHOOK: bool = False
    WEBHOOK_HOST: Optional[str] = None
    WEBHOOK_PATH: str = "/webhook/telegram"
    WEBHOOK_SECRET: SecretStr = SecretStr("secret-webhook-key")

    # FastAPI Server
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    JWT_SECRET: SecretStr = SecretStr("super-secret-jwt-key")
    JWT_ALGORITHM: str = "HS256"

    # PostgreSQL Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    
    # Redis Cache & Broker
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value() if isinstance(self.POSTGRES_PASSWORD, SecretStr) else self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @field_validator("JWT_SECRET", "WEBHOOK_SECRET")
    @classmethod
    def forbid_default_secrets_in_prod(cls, v: SecretStr, info) -> SecretStr:
        # FIX: запрет дефолтных секретов-заглушек в production
        weak_defaults = {"super-secret-jwt-key", "secret-webhook-key"}
        if v.get_secret_value() in weak_defaults:
            import os
            if os.getenv("ENV") == "production":
                raise ValueError(f"{info.field_name}: hardcoded default secret is forbidden in production")
        return v


settings = Settings()
