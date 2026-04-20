"""Smoke tests for the Celery application scaffold."""

from __future__ import annotations

from celery import Celery

from app.tasks import celery_app
from app.tasks.scheduled_posts import check_scheduled_posts


def test_celery_app_is_configured() -> None:
    assert isinstance(celery_app, Celery)
    assert celery_app.main == "sns_calendar"
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.timezone == "Asia/Tokyo"


def test_beat_schedule_includes_check_scheduled_posts() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "check-scheduled-posts-every-minute" in schedule
    entry = schedule["check-scheduled-posts-every-minute"]
    assert entry["task"] == "app.tasks.scheduled_posts.check_scheduled_posts"


def test_check_scheduled_posts_is_registered() -> None:
    task_name = "app.tasks.scheduled_posts.check_scheduled_posts"
    assert task_name in celery_app.tasks


def test_check_scheduled_posts_returns_status_ok() -> None:
    result = check_scheduled_posts.run()
    assert result["status"] == "ok"
    assert "checked_at" in result
