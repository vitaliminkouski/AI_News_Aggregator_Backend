from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import feedparser
import newspaper
import requests

logger = logging.getLogger(__name__)

USER_AGENT = "newsagent-bot/0.1 (+https://example.com/contact)"


def is_rss(url: str) -> bool:
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        text_lower = response.text.lower()
        return "xml" in content_type or "<rss" in text_lower or "<feed" in text_lower
    except requests.RequestException as exc:
        logger.warning("Unable to detect feed type for %s: %s", url, exc)
        return False


def parse_news(url: str, limit: int = 30) -> List[Dict[str, Optional[str]]]:
    if is_rss(url):
        return parse_rss(url, limit)
    return parse_html(url, limit)


def parse_html(url: str, limit: int) -> List[Dict[str, Optional[str]]]:
    articles_data: List[Dict[str, Optional[str]]] = []
    try:
        source = newspaper.build(url, memoize_articles=False)
    except Exception as exc:  # pragma: no cover - network failures
        logger.error("Cannot access %s: %s", url, exc)
        return articles_data

    for article in source.articles[:limit]:
        parsed = _process_article(article.url)
        if parsed:
            articles_data.append(parsed)
    return articles_data


def parse_rss(url: str, limit: int) -> List[Dict[str, Optional[str]]]:
    articles_data: List[Dict[str, Optional[str]]] = []
    try:
        feed = feedparser.parse(url)
    except Exception as exc:  # pragma: no cover - invalid feed
        logger.error("Cannot parse feed %s: %s", url, exc)
        return articles_data

    for entry in feed.entries[:limit]:
        link = entry.get("link")
        if not link:
            continue
        parsed = _process_article(link)
        if not parsed:
            continue
        published_at = _convert_entry_date(entry)
        parsed["published_at"] = published_at
        articles_data.append(parsed)
    return articles_data


def _process_article(url: str) -> Optional[Dict[str, Optional[str]]]:
    article = newspaper.Article(url)
    try:
        article.download()
        article.parse()
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to parse %s: %s", url, exc)
        return None

    if not article.text:
        return None
    return {
        "title": article.title,
        "text": article.text,
        "top_image": getattr(article, "top_image", None),
        "published_at": article.publish_date,
        "url": url,
    }


def _convert_entry_date(entry) -> Optional[datetime]:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
    except Exception:  # pragma: no cover - fallback parsing
        return None
