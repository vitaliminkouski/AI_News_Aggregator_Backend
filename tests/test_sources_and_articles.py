import types

import pytest


@pytest.mark.anyio
async def test_create_and_list_sources(client):
    payload = {
        "source_name": "Example Feed",
        "source_url": "https://example.com/rss",
        "language": "en",
    }
    response = await client.post("/api/v1/sources/", json=payload)
    assert response.status_code == 201
    source = response.json()
    assert source["source_name"] == "Example Feed"
    assert source["is_active"] is True

    response = await client.get("/api/v1/sources/")
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) == 1
    assert sources[0]["source_url"] == "https://example.com/rss"

    source_id = source["id"]
    patch_resp = await client.patch(
        f"/api/v1/sources/{source_id}",
        json={"source_name": "Updated Feed", "is_active": False},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["source_name"] == "Updated Feed"
    assert patched["is_active"] is False

    delete_resp = await client.delete(f"/api/v1/sources/{source_id}")
    assert delete_resp.status_code == 204


@pytest.mark.anyio
async def test_ingest_articles_flow(client, monkeypatch):
    # Create source
    payload = {
        "source_name": "Example Feed",
        "source_url": "https://example.com/rss",
    }
    create_resp = await client.post("/api/v1/sources/", json=payload)
    source_id = create_resp.json()["id"]

    fake_articles = [
        {
            "title": "Central bank raises rates",
            "text": "Bank of Nowhere has increased rates significantly.",
            "url": "https://example.com/article",
            "published_at": None,
        }
    ]

    monkeypatch.setattr("app.services.news_ingestion.parse_news", lambda *_, **__: fake_articles)

    async def fake_analyze(text: str, **kwargs):
        sentiment = types.SimpleNamespace(label="positive", score=0.9)
        entities = [
            types.SimpleNamespace(text="Bank of Nowhere", type="ORG", score=0.95),
        ]
        return types.SimpleNamespace(summary="Summary", sentiment=sentiment, entities=entities)

    monkeypatch.setattr("app.services.news_ingestion.ml_client", types.SimpleNamespace(analyze=fake_analyze))

    ingest_resp = await client.post("/api/v1/articles/ingest", json={"source_ids": [source_id], "limit": 1})
    assert ingest_resp.status_code == 202
    body = ingest_resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sentiment_label"] == "positive"

    list_resp = await client.get("/api/v1/articles")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 1
    assert data["items"][0]["summary"] == "Summary"
    assert data["items"][0]["source"]["id"] == source_id

    article_id = data["items"][0]["id"]
    detail_resp = await client.get(f"/api/v1/articles/{article_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["sentiment_score"] == pytest.approx(0.9)
