import os
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings=get_settings()

celery_app = Celery(
    "news_bot",
    broker= settings.CELERY_BROKER_URL,
    backend= settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Расписание Beat
celery_app.conf.beat_schedule = {
    "parse-news-every-30-minutes": {
        "task": "app.tasks.news_tasks.run_news_pipeline",
        "schedule": crontab(*settings.INGEST_CRON.split())
    },
}

celery_app.autodiscover_tasks(['app.tasks'])