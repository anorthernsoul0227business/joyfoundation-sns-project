from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import notifications as notifications_api
from app.core.security import CurrentUser, get_current_user
from app.main import app


@dataclass
class FakeResponse:
    data: list[dict[str, Any]]


class FakeNotificationsQuery:
    def __init__(self, client: FakeNotificationsClient, table_name: str) -> None:
        self.client = client
        self.table_name = table_name
        self._action = "select"
        self._update_values: dict[str, Any] | None = None
        self._insert_values: dict[str, Any] | None = None
        self._eq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []
        self._order: tuple[str, bool] | None = None
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None

    def select(self, _columns: str) -> FakeNotificationsQuery:
        self._action = "select"
        return self

    def update(self, values: dict[str, Any]) -> FakeNotificationsQuery:
        self._action = "update"
        self._update_values = values
        return self

    def insert(self, values: dict[str, Any]) -> FakeNotificationsQuery:
        self._action = "insert"
        self._insert_values = values
        return self

    def eq(self, column: str, value: Any) -> FakeNotificationsQuery:
        self._eq_filters.append((column, value))
        return self

    def is_(self, column: str, value: str) -> FakeNotificationsQuery:
        if value == "null":
            self._null_filters.append(column)
        return self

    def order(self, column: str, *, desc: bool = False) -> FakeNotificationsQuery:
        self._order = (column, desc)
        return self

    def range(self, start: int, end_inclusive: int) -> FakeNotificationsQuery:
        self._range = (start, end_inclusive)
        return self

    def limit(self, count: int) -> FakeNotificationsQuery:
        self._limit = count
        return self

    def _filtered(self) -> list[dict[str, Any]]:
        rows = list(self.client.notifications)
        for column, value in self._eq_filters:
            rows = [row for row in rows if row.get(column) == value]
        for column in self._null_filters:
            rows = [row for row in rows if row.get(column) is None]
        if self._order is not None:
            column, desc = self._order
            rows.sort(key=lambda r: r.get(column) or "", reverse=desc)
        if self._range is not None:
            start, end_inclusive = self._range
            rows = rows[start : end_inclusive + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def execute(self) -> FakeResponse:
        if self._action == "insert" and self._insert_values is not None:
            row = {
                "id": str(uuid4()),
                "created_at": datetime.now(UTC).isoformat(),
                "read_at": None,
                **self._insert_values,
            }
            self.client.notifications.append(row)
            return FakeResponse([row])
        if self._action == "update" and self._update_values is not None:
            updated: list[dict[str, Any]] = []
            for row in self._filtered():
                row.update(self._update_values)
                updated.append(dict(row))
            return FakeResponse(updated)
        return FakeResponse([dict(row) for row in self._filtered()])


@dataclass
class FakeNotificationsClient:
    notifications: list[dict[str, Any]] = field(default_factory=list)

    def table(self, name: str) -> FakeNotificationsQuery:
        return FakeNotificationsQuery(self, name)


@pytest.fixture
def fake_client() -> FakeNotificationsClient:
    return FakeNotificationsClient()


@pytest.fixture
def authenticated_client(
    fake_client: FakeNotificationsClient,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, str]]:
    user_id = str(uuid4())
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email="tester@example.com",
        role="authenticated",
        access_token="test-token",
    )
    monkeypatch.setattr(
        notifications_api,
        "get_supabase_client",
        lambda: fake_client,
    )
    try:
        yield TestClient(app), user_id
    finally:
        app.dependency_overrides.clear()


def _seed(
    client: FakeNotificationsClient,
    user_id: str,
    *,
    count: int = 3,
    unread: int = 2,
) -> None:
    base = datetime.now(UTC)
    for index in range(count):
        client.notifications.append(
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "kind": "post_published",
                "title": f"通知 {index}",
                "body": f"body {index}",
                "related_post_id": str(uuid4()),
                "read_at": None
                if index < unread
                else (base - timedelta(minutes=index)).isoformat(),
                "created_at": (base - timedelta(minutes=index)).isoformat(),
            }
        )


def test_list_returns_items_and_counts(
    authenticated_client: tuple[TestClient, str],
    fake_client: FakeNotificationsClient,
) -> None:
    client, user_id = authenticated_client
    _seed(fake_client, user_id, count=3, unread=2)

    response = client.get("/api/notifications")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    assert body["unread_count"] == 2
    assert body["total"] == 3


def test_list_filter_unread_only(
    authenticated_client: tuple[TestClient, str],
    fake_client: FakeNotificationsClient,
) -> None:
    client, user_id = authenticated_client
    _seed(fake_client, user_id, count=4, unread=2)

    response = client.get("/api/notifications", params={"unread_only": True})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert item["read_at"] is None


def test_list_does_not_leak_other_users(
    authenticated_client: tuple[TestClient, str],
    fake_client: FakeNotificationsClient,
) -> None:
    client, user_id = authenticated_client
    _seed(fake_client, user_id, count=1, unread=1)
    fake_client.notifications.append(
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "kind": "post_published",
            "title": "他人の通知",
            "body": None,
            "related_post_id": None,
            "read_at": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )

    response = client.get("/api/notifications")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "通知 0"


def test_mark_notification_read(
    authenticated_client: tuple[TestClient, str],
    fake_client: FakeNotificationsClient,
) -> None:
    client, user_id = authenticated_client
    _seed(fake_client, user_id, count=1, unread=1)
    target_id = fake_client.notifications[0]["id"]

    response = client.post(f"/api/notifications/{target_id}/read")

    assert response.status_code == 200
    assert response.json()["read_at"] is not None
    assert fake_client.notifications[0]["read_at"] is not None


def test_mark_notification_read_is_idempotent(
    authenticated_client: tuple[TestClient, str],
    fake_client: FakeNotificationsClient,
) -> None:
    client, user_id = authenticated_client
    _seed(fake_client, user_id, count=1, unread=0)
    target_id = fake_client.notifications[0]["id"]

    response = client.post(f"/api/notifications/{target_id}/read")

    assert response.status_code == 200


def test_mark_notification_read_404_when_other_user(
    authenticated_client: tuple[TestClient, str],
    fake_client: FakeNotificationsClient,
) -> None:
    client, _user_id = authenticated_client
    other_row_id = str(uuid4())
    fake_client.notifications.append(
        {
            "id": other_row_id,
            "user_id": str(uuid4()),
            "kind": "post_published",
            "title": "他人",
            "body": None,
            "related_post_id": None,
            "read_at": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )

    response = client.post(f"/api/notifications/{other_row_id}/read")

    assert response.status_code == 404


def test_mark_all_read(
    authenticated_client: tuple[TestClient, str],
    fake_client: FakeNotificationsClient,
) -> None:
    client, user_id = authenticated_client
    _seed(fake_client, user_id, count=3, unread=3)

    response = client.post("/api/notifications/read-all")

    assert response.status_code == 200
    assert response.json()["updated_count"] == 3
    for row in fake_client.notifications:
        assert row["read_at"] is not None


def test_list_requires_authentication() -> None:
    client = TestClient(app)
    response = client.get("/api/notifications")
    assert response.status_code == 401
