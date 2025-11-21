# News_Bot
Follow this steps to run server on local machine:
1. Clone repository
2. Install Docker, Docker-compose
3. Get file .env from developers and copy to project root directory(to directory news_bot_backend). Make sure it contains `ML_SERVICE_URL` pointing to the deployed ML microservice (default `http://ml-service:8100`).
4. Build and run container with command "docker-compose up --build"

## Working with the ingestion API
1. Add a source:
   ```bash
   curl -X POST http://localhost:8000/api/v1/sources/ \
        -H "Content-Type: application/json" \
        -d '{"source_name": "Example", "source_url": "https://example.com/rss"}'
   ```
2. Trigger parsing + ML enrichment:
   ```bash
   curl -X POST http://localhost:8000/api/v1/articles/ingest \
        -H "Content-Type: application/json" \
        -d '{"source_ids": [1], "limit": 5}'
   ```
3. Read processed items:
   ```bash
   curl "http://localhost:8000/api/v1/articles?limit=20&source_id=1"
   ```

Articles returned by the API already contain summary, sentiment, extracted entities and metadata that могут напрямую отображаться на фронтенде.

## Background ingestion
- `docker-compose.yml` разворачивает Redis, Celery worker и Celery beat. Настрой `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `INGEST_CRON` в `.env`.
- Периодические задания выполняют `POST /api/v1/articles/ingest` автоматически и сохраняют результаты в Postgres.
- Логи воркеров доступны через `docker compose logs worker` / `logs beat`.

## Тесты
```bash
cd news_bot_backend
pip install -r requirements.txt
python -m pytest
```

`tests/` содержит интеграционные сценарии для CRUD источников и пайплайна инжеста, включая мокирование парсера и ML сервиса.
