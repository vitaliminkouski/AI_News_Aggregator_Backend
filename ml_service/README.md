# NewsAgent ML Microservice

Сервис предоставляет REST API для оффлайн‑инференса моделей саммаризации, анализа тональности и NER. Построен на FastAPI и использует Hugging Face `transformers`.

## Возможности
- `POST /v1/summarize` — генерирует краткое саммари для переданного текста.
- `POST /v1/sentiment` — определяет тональность и уверенность.
- `POST /v1/ner` — извлекает именованные сущности с типами.
- `POST /v1/analyze` — запускает полный конвейер (саммари + тональность + NER).
- `GET /health` — проверка доступности сервиса.

## Запуск локально
```bash
cd ml_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8100
```

Переменные окружения можно задать в `.env` (см. `app/core/config.py`), например:
```
SUMMARIZATION_MODEL_NAME=sshleifer/distilbart-cnn-12-6
SENTIMENT_MODEL_NAME=cointegrated/rubert-tiny
NER_MODEL_NAME=dslim/bert-base-NER
TORCH_DEVICE=cpu
```

## Docker
```bash
cd ml_service
docker build -t newsagent-ml .
docker run --rm -p 8100:8100 --env-file .env newsagent-ml
```

## Предзагрузка моделей
Чтобы заранее скачать веса с Hugging Face (например, для офлайн-среды), выполните:

```bash
python ml_service/scripts/download_models.py --local-dir ./hf_models
```

Скрипт использует текущие настройки (`app/core/config.py`) и загружает модели в указанный каталог (либо в кеш `~/.cache/huggingface`).

## Деплой на Render.com
Dockerfile в `ml_service/` уже скачивает нужные веса при сборке в каталог `/srv/models` и задаёт переменные окружения `HF_HOME`, `TRANSFORMERS_CACHE`, `SENTENCEPIECE_CACHE`, чтобы сервис работал без доступа к интернету.

Шаги:
1. Собери образ локально и залей в регистри (например, Render Registry или GHCR):  
   `docker build -t <registry>/newsagent-ml:latest ml_service`
2. На Render создай Web Service c источником образа или Git-репозиторием и укажи путь к Dockerfile (`ml_service/Dockerfile`).
3. В переменные окружения добавь минимум:  
   - `APP_NAME`, `VERSION` (опционально)  
   - `SUMMARIZATION_MODEL_NAME=/srv/models/summarization`  
   - `SENTIMENT_MODEL_NAME=/srv/models/sentiment`  
   - `NER_MODEL_NAME=/srv/models/ner`  
   - `TORCH_DEVICE=cpu` (или `cuda` на GPU-плане)
4. Стартовая команда: `uvicorn app.main:app --host 0.0.0.0 --port 8100`
5. Установи health check на `GET /health`.

Остаётся сделать вручную:
- Создать сам сервис на Render, загрузить образ/подключить репозиторий и задать переменные окружения.
- Настроить маршрутизацию/секреты (например, приватный HF токен, если используешь закрытые модели).
- Связать ML-сервис с backend (добавить URL в конфигурацию основного приложения).

## Формат запросов
```bash
curl -X POST http://localhost:8100/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Банк России повысил ключевую ставку на 1 п.п. на заседании в пятницу."}'
```

Ответ:
```json
{
  "summary": "...",
  "sentiment": {"label": "positive", "score": 0.71},
  "entities": [{"text": "Банк России", "type": "ORG", "score": 0.98}]
}
```

## Интеграция
Сервис задуман как отдельный микросервис. Бэкенд NewsAgent может отправлять запросы к `http://ml-service:8100` (Docker Compose) или использовать библиотеку клиентов (в планах). Пайплайн реализует асинхронные методы и выполняет тяжёлые вычисления в отдельном потоке, поэтому вызовы не блокируют event loop FastAPI.
