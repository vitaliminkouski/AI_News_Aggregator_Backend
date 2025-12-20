from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Iterable, List, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.articles import Articles
from app.models.source import Source
from app.services.ml_client import ml_client
from app.services.news_parser import parse_news


def _hash_content(title: str | None, content: str) -> str:
    payload = (title or "") + content
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def ingest_sources(
    db: AsyncSession,
    *,
    source_ids: Sequence[int] | None = None,
    limit: int = 20,
) -> List[Articles]:
    query = select(Source).where(Source.is_active.is_(True))
    if source_ids:
        query = query.where(Source.id.in_(source_ids))

    result = await db.execute(query)
    sources = result.scalars().all()
    created: List[Articles] = []

    for source in sources:
        articles_raw = await asyncio.to_thread(parse_news, source.source_url, limit)
        if not articles_raw:
            continue

        for raw in articles_raw:
            text = raw.get("text")
            if not text:
                continue
            content_hash = _hash_content(raw.get("title"), text)
            exists = await db.execute(
                select(Articles.id).where(Articles.content_hash == content_hash)
            )
            if exists.scalar_one_or_none():
                continue

            analysis = await ml_client.analyze(text)
            article = Articles(
                title=raw.get("title"),
                summary=analysis.summary,
                content=text,
                url=raw.get("url"),
                image_url=raw.get("top_image"),
                published_at=_coerce_datetime(raw.get("published_at")),
                fetched_at=datetime.utcnow(),
                source_id=source.id,
                topic_id=source.topic_id,  # Добавляем topic_id из source
                content_hash=content_hash,
                sentiment_label=analysis.sentiment.label,
                sentiment_score=analysis.sentiment.score,
                entities=[
                    {"text": entity.text, "type": entity.type, "score": entity.score}
                    for entity in analysis.entities
                ],
            )
            db.add(article)
            created.append(article)

        await db.execute(
            update(Source)
            .where(Source.id == source.id)
            .values(last_fetched_at=datetime.utcnow())
        )

    await db.commit()
    return created


def _coerce_datetime(value):
    if isinstance(value, datetime):
        return value
    return None
