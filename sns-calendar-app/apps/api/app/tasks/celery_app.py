"""Celery application singleton.

Workers and beat schedulers consume this module:
    celery -A app.tasks.celery_app worker --loglevel=info
    celery -A app.tasks.celery_app beat --loglevel=info
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab


def _build_celery() -> Celery:
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    backend_url = os.environ.get("CELERY_RESULT_BACKEND", broker_url)

    app = Celery(
        "sns_calendar",
        broker=broker_url,
        backend=backend_url,
        include=["app.tasks.scheduled_posts"],
    )

    app.conf.update(
        task_default_queue="default",
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        timezone="Asia/Tokyo",
        enable_utc=True,
        beat_schedule={
            "check-scheduled-posts-every-minute": {
                "task": "app.tasks.scheduled_posts.check_scheduled_posts",
                "schedule": crontab(minute="*"),
            },
        },
    )

    return app


celery_app = _build_celery()
