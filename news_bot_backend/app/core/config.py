from typing import Optional

from pydantic import Field
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # APP SETTINGS
    APP_NAME: str
    VERSION: str

    ENVIRONMENT: str
    DEBUG: bool = True
    API_PREFIX: str

    # DATABASE
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DATABASE_URL: Optional[str] = None
    ASYNC_DATABASE_URL: Optional[str] = None

    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ML services
    ML_SERVICE_URL: str = Field(
        default="http://ml-service:8100",
        description="Base URL of the NewsAgent ML microservice.",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def get_async_db_url(self):
        if self.ASYNC_DATABASE_URL:
            return self.ASYNC_DATABASE_URL
        else:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

    @property
    def get_sync_db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
