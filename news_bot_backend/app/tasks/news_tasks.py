import asyncio
from app.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.models import Source, Articles, UserSources
from app.services.news_parser import parse_news
from app.services.ml_client import get_summary_from_ml
from sqlalchemy import select
from app.core.config import get_settings

settings=get_settings()


def run_async(coro):
    """Помощник для запуска асинхронных функций в синхронном Celery."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return asyncio.ensure_future(coro)
    return loop.run_until_complete(coro)


@celery_app.task(name="app.tasks.news_tasks.run_news_pipeline")
def run_news_pipeline():
    return run_async(process_all_sources())


async def process_all_sources():
    async with AsyncSessionLocal() as session:
        # 1. Получаем все активные источники
        stmt = select(Source).where(Source.is_active == True)
        sources = (await session.execute(stmt)).scalars().all()

        for source in sources:
            # 2. Парсим статьи (наш быстрый ThreadPool парсер)
            articles_data = parse_news(source.source_url, limit=10, lang=source.language)

            for item in articles_data:
                # 3. Проверка на дубликат по URL
                exist_stmt = select(Articles).where(Articles.url == item['url'])
                if (await session.execute(exist_stmt)).scalar():
                    continue

                # 4. Суммаризация через ML сервис
                summary_text = await get_summary_from_ml(item['text'])

                # 5. Сохранение
                new_article = Articles(
                    title=item['title'],
                    summary=summary_text,
                    image_url=item['image_url'],
                    url=item['url'],
                    published_at=item['published_at'],
                    source_id=source.id,
                    topic_id=source.topic_id
                )
                session.add(new_article)

        await session.commit()


@celery_app.task(name="app.tasks.news_tasks.sync_user_sources")
def sync_user_sources_task(user_id: int):
    """Фоновая задача для синхронизации новостей конкретного пользователя."""
    return run_async(process_user_news(user_id))


async def process_user_news(user_id: int):
    async with AsyncSessionLocal() as session:
        # 1. Получаем все источники, на которые подписан пользователь
        stmt = (
            select(Source)
            .join(UserSources, UserSources.source_id == Source.id)
            .where(UserSources.user_id == user_id)
            .where(Source.is_active == True)
        )
        result = await session.execute(stmt)
        sources = result.scalars().all()

        if not sources:
            return f"No active sources for user {user_id}"

        for source in sources:
            # 2. Парсим новости для источника
            # Используем настройки лимита из нашего config.py
            news_items = parse_news(
                source.source_url,
                limit=settings.MAX_ARTICLES_PER_SOURCE,
                lang=source.language
            )

            for item in news_items:
                # 3. Дедупликация (проверяем, есть ли уже такая ссылка в БД)
                exists_stmt = select(Articles).where(Articles.url == item['url'])
                exists_res = await session.execute(exists_stmt)
                if exists_res.scalar():
                    continue

                # 4. Суммаризация через ML сервис
                summary = await get_summary_from_ml(item['text'])

                # 5. Сохранение в БД
                new_article = Articles(
                    title=item['title'],
                    summary=summary,
                    image_url=item['image_url'],
                    url=item['url'],
                    published_at=item['published_at'],
                    source_id=source.id,
                    topic_id=source.topic_id
                )
                session.add(new_article)

        await session.commit()
        return f"Sync completed for user {user_id}"