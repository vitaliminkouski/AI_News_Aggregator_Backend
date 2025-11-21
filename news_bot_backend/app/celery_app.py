from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "newsagent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

def _parse_cron(expr: str) -> crontab:
    minute, hour, day_of_month, month_of_year, day_of_week = expr.split()
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


celery_app.conf.update(
    timezone="UTC",
    task_serializer="json",
    beat_schedule={
        "scheduled-ingestion": {
            "task": "app.tasks.ingest.run_auto_ingest",
            "schedule": _parse_cron(settings.INGEST_CRON),
            "options": {"queue": "ingest"},
        }
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
