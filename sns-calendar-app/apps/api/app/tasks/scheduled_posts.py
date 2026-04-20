"""Placeholder scheduled-post tasks.

WEB-008 does not wire real publishing logic. Actual implementation lands in
Sprint 3 (WEB-020 onwards). For now we expose a single beat-driven task that
returns a trivial payload so the worker + beat loop is observable from logs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.scheduled_posts.check_scheduled_posts")
def check_scheduled_posts() -> dict[str, str]:
    """Called every minute by Celery beat as the polling heartbeat."""
    return {
        "status": "ok",
        "checked_at": datetime.now(UTC).isoformat(),
    }
