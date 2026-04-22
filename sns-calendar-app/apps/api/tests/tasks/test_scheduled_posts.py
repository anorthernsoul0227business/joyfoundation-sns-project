from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from app.services.publisher.base import PublishResult
from app.tasks.celery_app import celery_app
from app.tasks.scheduled_posts import check_scheduled_posts, publish_post


@dataclass
class QueryResult:
    data: list[dict[str, Any]]


@dataclass
class FakeSupabaseClient:
    posts: dict[str, dict[str, Any]] = field(default_factory=dict)
    post_targets: dict[str, dict[str, Any]] = field(default_factory=dict)
    users: dict[str, dict[str, Any]] = field(default_factory=dict)

    def table(self, name: str) -> FakeTableQuery:
        return FakeTableQuery(self, name)


@dataclass
class FakeTableQuery:
    client: FakeSupabaseClient
    table_name: str
    filters: list[tuple[str, str, Any]] = field(default_factory=list)
    action: str = "select"
    update_values: dict[str, Any] | None = None
    limit_count: int | None = None

    def select(self, _columns: str) -> FakeTableQuery:
        self.action = "select"
        return self

    def update(self, values: dict[str, Any]) -> FakeTableQuery:
        self.action = "update"
        self.update_values = values
        return self

    def eq(self, column: str, value: Any) -> FakeTableQuery:
        self.filters.append(("eq", column, value))
        return self

    def lte(self, column: str, value: Any) -> FakeTableQuery:
        self.filters.append(("lte", column, value))
        return self

    def limit(self, count: int) -> FakeTableQuery:
        self.limit_count = count
        return self

    def execute(self) -> QueryResult:
        rows = self._rows()
        if self.action == "update":
            updated: list[dict[str, Any]] = []
            for row in rows:
                row.update(self.update_values or {})
                updated.append(dict(row))
            return QueryResult(updated)

        selected = [dict(row) for row in rows]
        if self.limit_count is not None:
            selected = selected[: self.limit_count]
        return QueryResult(selected)

    def _rows(self) -> list[dict[str, Any]]:
        if self.table_name == "posts":
            source = list(self.client.posts.values())
        elif self.table_name == "post_targets":
            source = list(self.client.post_targets.values())
        elif self.table_name == "users":
            source = list(self.client.users.values())
        else:
            raise AssertionError(f"Unsupported table: {self.table_name}")

        rows = source
        for operator, column, value in self.filters:
            if operator == "eq":
                rows = [row for row in rows if row.get(column) == value]
            elif operator == "lte":
                rows = [row for row in rows if row.get(column) is not None and row.get(column) <= value]
            else:  # pragma: no cover - defensive guard
                raise AssertionError(f"Unsupported filter: {operator}")
        return rows


@pytest.fixture(autouse=True)
def eager_celery() -> Any:
    previous_eager = celery_app.conf.task_always_eager
    previous_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    try:
        yield
    finally:
        celery_app.conf.task_always_eager = previous_eager
        celery_app.conf.task_eager_propagates = previous_propagates


def _post(
    post_id: str,
    *,
    status: str = "scheduled",
    scheduled_at: str = "2026-04-21T00:00:00+00:00",
    user_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": post_id,
        "org_id": str(uuid4()),
        "user_id": user_id,
        "status": status,
        "scheduled_at": scheduled_at,
        "published_at": None,
    }


def _target(
    target_id: str,
    post_id: str,
    *,
    platform: str = "x",
    status: str = "pending",
) -> dict[str, Any]:
    return {
        "id": target_id,
        "post_id": post_id,
        "platform": platform,
        "status": status,
        "platform_post_id": None,
        "error_message": None,
    }


def test_check_scheduled_posts_enqueues_due_posts_and_runs_publish_post_eagerly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    due_post_id = str(uuid4())
    future_post_id = str(uuid4())
    target_id = str(uuid4())
    client = FakeSupabaseClient(
        posts={
            due_post_id: _post(due_post_id, scheduled_at="2000-01-01T00:00:00+00:00"),
            future_post_id: _post(future_post_id, scheduled_at="2999-12-31T23:59:59+00:00"),
        },
        post_targets={
            target_id: _target(target_id, due_post_id),
        },
    )

    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr(
        "app.tasks.scheduled_posts.publish_target",
        lambda target_id: _mark_target_published(client, target_id),
    )

    result = check_scheduled_posts.run()

    assert result["enqueued_count"] == 1
    assert client.posts[due_post_id]["status"] == "published"
    assert client.posts[due_post_id]["published_at"] is not None
    assert client.posts[future_post_id]["status"] == "scheduled"
    assert client.post_targets[target_id]["status"] == "published"


def test_check_scheduled_posts_skips_post_when_conditional_update_loses_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_id = str(uuid4())
    target_id = str(uuid4())
    client = FakeSupabaseClient(
        posts={post_id: _post(post_id)},
        post_targets={target_id: _target(target_id, post_id)},
    )
    seen = {"first": False}
    original_table = client.table

    def racing_table(name: str) -> FakeTableQuery:
        query = original_table(name)
        original_execute = query.execute

        def execute() -> QueryResult:
            if (
                name == "posts"
                and query.action == "update"
                and ("eq", "status", "scheduled") in query.filters
                and not seen["first"]
            ):
                seen["first"] = True
                client.posts[post_id]["status"] = "publishing"
            return original_execute()

        query.execute = execute  # type: ignore[method-assign]
        return query

    monkeypatch.setattr(client, "table", racing_table)
    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr(
        "app.tasks.scheduled_posts.publish_target",
        lambda _target_id: pytest.fail("publish_target should not be called"),
    )

    result = check_scheduled_posts.run()

    assert result["enqueued_count"] == 0
    assert client.posts[post_id]["status"] == "publishing"
    assert client.post_targets[target_id]["status"] == "pending"


def test_publish_post_marks_parent_published_when_all_targets_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_id = str(uuid4())
    target_a = str(uuid4())
    target_b = str(uuid4())
    client = FakeSupabaseClient(
        posts={post_id: _post(post_id, status="publishing")},
        post_targets={
            target_a: _target(target_a, post_id, status="pending"),
            target_b: _target(target_b, post_id, status="pending"),
        },
    )

    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr(
        "app.tasks.scheduled_posts.publish_target",
        lambda target_id: _mark_target_published(client, target_id),
    )

    result = publish_post.run(post_id)

    assert result["parent_status"] == "published"
    assert client.posts[post_id]["status"] == "published"
    assert client.posts[post_id]["published_at"] is not None


def test_publish_post_marks_parent_failed_when_any_target_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_id = str(uuid4())
    ok_target = str(uuid4())
    failed_target = str(uuid4())
    client = FakeSupabaseClient(
        posts={post_id: _post(post_id, status="publishing")},
        post_targets={
            ok_target: _target(ok_target, post_id, status="pending"),
            failed_target: _target(failed_target, post_id, status="pending"),
        },
    )

    def fake_publish(target_id: str) -> PublishResult:
        if target_id == ok_target:
            return _mark_target_published(client, target_id)
        client.post_targets[target_id]["status"] = "failed"
        client.post_targets[target_id]["error_message"] = "remote rejected"
        return PublishResult(False, None, "remote rejected")

    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr("app.tasks.scheduled_posts.publish_target", fake_publish)

    result = publish_post.run(post_id)

    assert result["parent_status"] == "failed"
    assert client.posts[post_id]["status"] == "failed"
    assert client.posts[post_id]["published_at"] is None


def test_publish_post_leaves_parent_publishing_when_all_targets_are_already_done_or_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_id = str(uuid4())
    published_target_id = str(uuid4())
    skipped_target_id = str(uuid4())
    client = FakeSupabaseClient(
        posts={post_id: _post(post_id, status="publishing")},
        post_targets={
            published_target_id: _target(published_target_id, post_id, status="published"),
            skipped_target_id: _target(skipped_target_id, post_id, status="skipped"),
        },
    )

    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr(
        "app.tasks.scheduled_posts.publish_target",
        lambda _target_id: pytest.fail("publish_target should not be called"),
    )

    result = publish_post.run(post_id)

    assert result["parent_status"] == "publishing"
    assert client.posts[post_id]["status"] == "publishing"
    assert client.posts[post_id]["published_at"] is None


def test_publish_post_marks_target_failed_when_publish_target_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_id = str(uuid4())
    target_id = str(uuid4())
    client = FakeSupabaseClient(
        posts={post_id: _post(post_id, status="publishing")},
        post_targets={target_id: _target(target_id, post_id, status="pending")},
    )

    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr(
        "app.tasks.scheduled_posts.publish_target",
        lambda _target_id: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = publish_post.run(post_id)

    assert result["parent_status"] == "failed"
    assert client.post_targets[target_id]["status"] == "failed"
    assert client.post_targets[target_id]["error_message"] == "boom"
    assert result["results"][0]["error"] == "unhandled: boom"


def test_publish_post_dispatches_notification_with_mixed_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = str(uuid4())
    post_id = str(uuid4())
    ok_target = str(uuid4())
    failed_target = str(uuid4())
    client = FakeSupabaseClient(
        posts={post_id: _post(post_id, status="publishing", user_id=user_id)},
        post_targets={
            ok_target: _target(ok_target, post_id, platform="x", status="pending"),
            failed_target: _target(
                failed_target, post_id, platform="instagram", status="pending"
            ),
        },
        users={user_id: {"id": user_id, "email": "owner@example.com"}},
    )

    def fake_publish(target_id: str) -> PublishResult:
        if target_id == ok_target:
            return _mark_target_published(client, target_id)
        client.post_targets[target_id]["status"] = "failed"
        client.post_targets[target_id]["error_message"] = "token expired"
        return PublishResult(False, None, "token expired")

    calls: list[dict[str, Any]] = []

    def fake_notifier(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr("app.tasks.scheduled_posts.publish_target", fake_publish)

    publish_post.run(post_id, notifier=fake_notifier)

    assert len(calls) == 1
    call = calls[0]
    assert call["post_id"] == post_id
    assert call["owner_email"] == "owner@example.com"
    summary = call["summary"]
    assert len(summary["success"]) == 1
    assert summary["success"][0]["platform"] == "x"
    assert len(summary["failed"]) == 1
    assert summary["failed"][0]["platform"] == "instagram"
    assert summary["failed"][0]["error"] == "token expired"


def test_publish_post_skips_notification_when_user_email_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = str(uuid4())
    post_id = str(uuid4())
    target_id = str(uuid4())
    client = FakeSupabaseClient(
        posts={post_id: _post(post_id, status="publishing", user_id=user_id)},
        post_targets={target_id: _target(target_id, post_id, status="pending")},
        users={},
    )

    monkeypatch.setattr("app.tasks.scheduled_posts.get_supabase_client", lambda: client)
    monkeypatch.setattr(
        "app.tasks.scheduled_posts.publish_target",
        lambda target_id: _mark_target_published(client, target_id),
    )

    def fail_if_called(**kwargs: Any) -> None:
        pytest.fail("notifier should not be called when user email cannot be resolved")

    publish_post.run(post_id, notifier=fail_if_called)


def _mark_target_published(client: FakeSupabaseClient, target_id: str) -> PublishResult:
    client.post_targets[target_id]["status"] = "published"
    client.post_targets[target_id]["platform_post_id"] = f"post-{target_id}"
    client.post_targets[target_id]["error_message"] = None
    return PublishResult(True, f"post-{target_id}", None)
