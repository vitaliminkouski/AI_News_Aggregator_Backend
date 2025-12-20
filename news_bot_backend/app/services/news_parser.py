from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
from typing import Dict, List, Optional

import feedparser
import newspaper
from newspaper import Article, Config
from app.core.logging_config import get_logger

logger = get_logger(__name__)

USER_AGENT = "newsagent-bot/0.1 (+https://example.com/contact)"


def get_newspaper_config(lang: str = 'ru') -> Config:
    config = Config()
    config.browser_user_agent = USER_AGENT
    config.request_timeout = 10
    config.language = lang
    config.memoize_articles = False
    config.fetch_images = True
    return config


def _make_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _process_article(url: str, rss_date: Optional[datetime] = None, lang: str = 'ru') -> Optional[Dict]:

    config = get_newspaper_config(lang)
    article = Article(url, config=config)

    try:
        article.download()
        article.parse()

        # Если текста слишком мало, скорее всего, это ошибка или страница-заглушка
        if not article.text or len(article.text) < 100:
            return None

        pub_date = _make_utc_aware(rss_date) or _make_utc_aware(article.publish_date)

        return {
            "title": article.title,
            "text": article.text,
            "image_url": getattr(article, "top_image", None),
            "published_at": pub_date,
            "url": url,
        }
    except Exception as exc:
        # logger.warning("Failed to parse %s: %s", url, exc)
        return None


def parse_news(url: str, limit: int = 20, lang: str = 'ru') -> List[Dict]:

    urls_to_process: List[tuple[str, Optional[datetime]]] = []

    # Пробуем собрать ссылки через RSS
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            # logger.info("Source %s detected as RSS", url)
            for entry in feed.entries[:limit]:
                # Извлекаем дату из RSS, если она есть
                dt = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                urls_to_process.append((entry.link, dt))
        else:
            # Если RSS пуст, пробуем собрать ссылки как с обычной HTML страницы
            # logger.info("Source %s detected as HTML, building...", url)
            source = newspaper.build(url, config=get_newspaper_config(lang))
            for art in source.articles[:limit]:
                urls_to_process.append((art.url, None))
    except Exception as e:
        logger.error("Error gathering URLs from %s: %s", url, e)
        return []

    # Параллельная обработка собранных ссылок
    articles_data: List[Dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Создаем задачи
        future_to_url = {
            executor.submit(_process_article, link, dt, lang): link
            for link, dt in urls_to_process
        }

        # Собираем результаты по мере завершения
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    articles_data.append(data)
            except Exception as exc:
                pass
                logger.error("Thread generated an exception: %s", exc)

    # Сортируем результат по дате (свежие сверху), если даты есть
    articles_data.sort(
        key=lambda x: x['published_at'] if x['published_at'] else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )

    return articles_data

