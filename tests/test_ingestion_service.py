import types

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.services import news_ingestion
from app.tasks.ingest import run_auto_ingest


@pytest.mark.anyio
async def test_ingest_sources_deduplicates(session_factory, monkeypatch):
    async with session_factory() as session:  # type: AsyncSession
        source = Source(source_name="Example", source_url="https://example.com/rss")
        session.add(source)
        await session.commit()
        await session.refresh(source)

        fake_articles = [
            {
                "title": "News 1",
                "text": "Hello world",
                "url": "https://example.com/a",
                "published_at": None,
            },
            {
                "title": "News 1",
                "text": "Hello world",
                "url": "https://example.com/a",
                "published_at": None,
            },
        ]
        monkeypatch.setattr("app.services.news_ingestion.parse_news", lambda *_, **__: fake_articles)

        async def fake_analyze(*args, **kwargs):
            sentiment = types.SimpleNamespace(label="neutral", score=0.5)
            return types.SimpleNamespace(summary="Summary", sentiment=sentiment, entities=[])

        monkeypatch.setattr("app.services.news_ingestion.ml_client", types.SimpleNamespace(analyze=fake_analyze))

        created = await news_ingestion.ingest_sources(session, source_ids=[source.id], limit=5)
        assert len(created) == 1


def test_celery_task(monkeypatch):
    async def fake_run(*args, **kwargs):
        return 2

    monkeypatch.setattr("app.tasks.ingest._run_ingest", fake_run)
    result = run_auto_ingest([1], limit=5)
    assert result == 2
