from __future__ import annotations

import asyncio
from typing import Sequence

from app.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.services.news_ingestion import ingest_sources


async def _run_ingest(source_ids: Sequence[int] | None, limit: int) -> int:
    async with AsyncSessionLocal() as session:
        articles = await ingest_sources(session, source_ids=source_ids, limit=limit)
    return len(articles)


@celery_app.task(name="app.tasks.ingest.run_auto_ingest")
def run_auto_ingest(source_ids: list[int] | None = None, limit: int = 10) -> int:
    """Celery task to fetch and enrich articles."""
    return asyncio.run(_run_ingest(source_ids, limit))

