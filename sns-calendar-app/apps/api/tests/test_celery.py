"""Smoke tests for the Celery application scaffold."""

from __future__ import annotations

from celery import Celery

from app.tasks import celery_app
from app.tasks.scheduled_posts import check_scheduled_posts, publish_post


def test_celery_app_is_configured() -> None:
    assert isinstance(celery_app, Celery)
    assert celery_app.main == "sns_calendar"
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.timezone == "Asia/Tokyo"


def test_beat_schedule_includes_check_scheduled_posts() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "check-scheduled-posts" in schedule
    entry = schedule["check-scheduled-posts"]
    assert entry["task"] == "app.tasks.scheduled_posts.check_scheduled_posts"
    assert entry["schedule"] == 60.0


def test_check_scheduled_posts_is_registered() -> None:
    task_name = "app.tasks.scheduled_posts.check_scheduled_posts"
    assert task_name in celery_app.tasks


def test_publish_post_is_registered() -> None:
    task_name = "app.tasks.scheduled_posts.publish_post"
    assert task_name in celery_app.tasks


def test_task_wrappers_expose_expected_names() -> None:
    assert check_scheduled_posts.name == "app.tasks.scheduled_posts.check_scheduled_posts"
    assert publish_post.name == "app.tasks.scheduled_posts.publish_post"


def test_check_scheduled_posts_returns_enqueued_count(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.tasks.scheduled_posts.get_supabase_client",
        lambda: _EmptySupabaseClient(),
    )

    result = check_scheduled_posts.run()

    assert "checked_at" in result
    assert result["enqueued_count"] == 0


class _EmptyQuery:
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return type("Result", (), {"data": []})()


class _EmptySupabaseClient:
    def table(self, _name: str) -> _EmptyQuery:
        return _EmptyQuery()
