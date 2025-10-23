from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass

_settings = get_settings()

engine = create_engine(_settings.get_sync_db_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

async_engine = create_async_engine(_settings.get_async_db_url)
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
