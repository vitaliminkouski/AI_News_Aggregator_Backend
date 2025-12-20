from functools import lru_cache
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    EMAIL_CONFIRM_EXPIRE_HOURS: int = 24
    ALGORITHM: str = "HS256"

    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_FROM_EMAIL: str = Field(default="")
    BACKEND_URL: str

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(levelname)s - %(asctime)s - %(name)s - %(message)s"
    
    # Log file settings
    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT: int = 5  # Keep 5 backup files
    LOG_TO_CONSOLE: bool = False  # Set to True if you also want console output

    PROFILE_PHOTOS_DIR: str = "static/profile_photos"

    # ML services
    ML_SERVICE_URL: str = Field(
        default="http://ml-service:8100/v1/summarize",  # Fixed: added /v1
        description="Full URL of the summarization endpoint.",
    )
    ML_TIMEOUT: int = Field(
        default=60,
        description="Timeout in seconds for ML service response."
    )

    # --- CELERY & PARSER ---
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/1")

    INGEST_CRON: str = Field(
        default="*/30 * * * *",
        description="Crontab expression for automatic ingestion schedule.",
    )

    MAX_ARTICLES_PER_SOURCE: int = Field(
        default=10,
        description="Limit articles per source per sync to avoid overloading."
    )

    PARSER_THREADS: int = Field(
        default=10,
        description="Number of concurrent threads for the news parser."
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
    return Settings()


settings = get_settings()
