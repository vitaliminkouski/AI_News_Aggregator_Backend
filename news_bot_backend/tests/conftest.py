# news_bot_backend/tests/conftest.py
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock
from datetime import datetime, timezone
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.db.database import Base, get_db
from app.models import User, Source, Articles, Topic, UserSources
from app.core.config import get_settings

# Используем существующую БД из настроек или переменную окружения
settings = get_settings()
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    settings.get_async_db_url  # Используем существующую БД
)


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Создает тестовую сессию БД."""
    # Используем существующую БД, но создаем транзакцию для отката
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Начинаем транзакцию
        trans = await session.begin()
        try:
            yield session
        finally:
            # Откатываем все изменения
            await trans.rollback()

    await engine.dispose()


# ... остальные фикстуры без изменений ...


@pytest_asyncio.fixture
async def test_user(test_db_session: AsyncSession):
    """Создает тестового пользователя."""
    from app.services.security import hash_password

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        is_verified=True,
        is_super=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_source(test_db_session: AsyncSession):
    """Создает тестовый источник."""
    source = Source(
        source_name="Test Source",
        source_url="https://example.com/rss",
        language="ru",
        is_active=True,
    )
    test_db_session.add(source)
    await test_db_session.commit()
    await test_db_session.refresh(source)
    return source


@pytest_asyncio.fixture
async def test_topic(test_db_session: AsyncSession):
    """Создает тестовый топик."""
    topic = Topic(name="Technology")
    test_db_session.add(topic)
    await test_db_session.commit()
    await test_db_session.refresh(topic)
    return topic


@pytest.fixture
def mock_settings(monkeypatch):
    """Мокирует настройки для тестов."""
    settings = Settings(
        SECRET_KEY="test_secret_key_" + "x" * 32,
        ML_SERVICE_URL="http://test-ml-service:8100/v1/summarize",
        ML_TIMEOUT=60,
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    return settings