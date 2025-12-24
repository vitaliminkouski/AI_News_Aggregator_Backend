# app/tasks/news_tasks.py
import asyncio
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.models import Source, Articles, UserSources, Topic
from app.services.news_parser import parse_news
from app.services.ml_client import get_summary_from_ml
from sqlalchemy import select
from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    """
    Конвертирует timezone-aware datetime в naive UTC.
    Если datetime уже naive, возвращает как есть.
    Если None, возвращает None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    # Конвертируем в UTC и убираем timezone info
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


async def _get_or_create_topic(session: AsyncSessionLocal, topic_name: str) -> int | None:
    """
    Получает существующий топик или создает новый.
    Возвращает topic_id или None, если topic_name пустой.
    """
    if not topic_name or not topic_name.strip():
        return None

    normalized_name = topic_name.strip()[:50]  # Ограничиваем длину

    # Ищем существующий топик
    stmt = select(Topic).where(Topic.name == normalized_name)
    result = await session.execute(stmt)
    existing_topic = result.scalar_one_or_none()

    if existing_topic:
        return existing_topic.id

    # Создаем новый топик
    try:
        new_topic = Topic(name=normalized_name)
        session.add(new_topic)
        await session.flush()  # Flush чтобы получить ID без commit
        logger.info(f"Created new topic: {normalized_name} (ID: {new_topic.id})")
        return new_topic.id
    except Exception as e:
        logger.error(f"Error creating topic '{normalized_name}': {e}", exc_info=True)
        # В случае ошибки (например, дубликат из-за race condition), пробуем найти снова
        result = await session.execute(stmt)
        existing_topic = result.scalar_one_or_none()
        if existing_topic:
            return existing_topic.id
        return None


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        raise RuntimeError("Cannot run async function: event loop is already running")

    return loop.run_until_complete(coro)


@celery_app.task(name="app.tasks.news_tasks.run_news_pipeline")
def run_news_pipeline():
    return run_async(process_all_sources())


async def process_all_sources():
    async with AsyncSessionLocal() as session:
        stmt = select(Source).where(Source.is_active == True)
        sources = (await session.execute(stmt)).scalars().all()

        for source in sources:
            try:
                articles_data = parse_news(source.source_url, limit=10, lang=source.language)

                for item in articles_data:
                    try:
                        exist_stmt = select(Articles).where(Articles.url == item['url'])
                        if (await session.execute(exist_stmt)).scalar():
                            continue

                        # Получаем summary (с fallback на первые 200 символов если ML недоступен)
                        try:
                            summary_text = await get_summary_from_ml(item['text'])
                        except Exception as e:
                            logger.error(
                                f"Failed to get summary for article {item.get('url', 'unknown')}, "
                                f"using fallback: {e}",
                                exc_info=True
                            )
                            # Fallback: первые 200 символов текста
                            summary_text = item['text'][:200] + "..." if len(item['text']) > 200 else item['text']

                        # Получаем или создаем топик, если он есть в статье
                        topic_id = source.topic_id  # По умолчанию используем топик источника
                        if 'topic' in item and item['topic']:
                            extracted_topic_id = await _get_or_create_topic(session, item['topic'])
                            if extracted_topic_id:
                                topic_id = extracted_topic_id
                                logger.debug(
                                    f"Assigned topic '{item['topic']}' to article {item.get('url', 'unknown')}")

                        pub_dt = _to_naive_utc(item.get('published_at')) or datetime.utcnow()
                        new_article = Articles(
                            title=item['title'],
                            summary=summary_text,
                            image_url=item['image_url'],
                            url=item['url'],
                            published_at=pub_dt,  # Без tzinfo
                            source_id=source.id,
                            topic_id=topic_id
                        )
                        session.add(new_article)
                    except Exception as e:
                        logger.error(f"Error processing article {item.get('url', 'unknown')}: {e}", exc_info=True)
                        continue

                # Update last_fetched_at
                source.last_fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)

            except Exception as e:
                logger.error(f"Error processing source {source.id} ({source.source_url}): {e}", exc_info=True)
                continue

        await session.commit()


@celery_app.task(name="app.tasks.news_tasks.sync_user_sources")
def sync_user_sources_task(user_id: int):
    """Фоновая задача для синхронизации новостей конкретного пользователя."""
    return run_async(process_user_news(user_id))


async def process_user_news(user_id: int):
    async with AsyncSessionLocal() as session:
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
            try:
                news_items = parse_news(
                    source.source_url,
                    limit=settings.MAX_ARTICLES_PER_SOURCE,
                    lang=source.language
                )

                for item in news_items:
                    try:
                        exists_stmt = select(Articles).where(Articles.url == item['url'])
                        exists_res = await session.execute(exists_stmt)
                        if exists_res.scalar():
                            continue

                        # Получаем summary (с fallback на первые 200 символов если ML недоступен)
                        try:
                            summary = await get_summary_from_ml(item['text'])
                        except Exception as e:
                            logger.error(
                                f"Failed to get summary for article {item.get('url', 'unknown')}, "
                                f"using fallback: {e}",
                                exc_info=True
                            )
                            # Fallback: первые 200 символов текста
                            summary = item['text'][:200] + "..." if len(item['text']) > 200 else item['text']

                        # Получаем или создаем топик, если он есть в статье
                        topic_id = source.topic_id  # По умолчанию используем топик источника
                        if 'topic' in item and item['topic']:
                            extracted_topic_id = await _get_or_create_topic(session, item['topic'])
                            if extracted_topic_id:
                                topic_id = extracted_topic_id
                                logger.debug(
                                    f"Assigned topic '{item['topic']}' to article {item.get('url', 'unknown')}")

                        pub_dt = _to_naive_utc(item.get('published_at')) or datetime.utcnow()
                        new_article = Articles(
                            title=item['title'],
                            summary=summary,
                            image_url=item['image_url'],
                            url=item['url'],
                            published_at=pub_dt,  # Без tzinfo
                            source_id=source.id,
                            topic_id=topic_id
                        )
                        session.add(new_article)
                    except Exception as e:
                        logger.error(f"Error processing article {item.get('url', 'unknown')}: {e}", exc_info=True)
                        continue
            except Exception as e:
                logger.error(f"Error processing source {source.id} ({source.source_url}): {e}", exc_info=True)
                continue

        await session.commit()
        return f"Sync completed for user {user_id}"
