"""End-to-end tests for WEB-013 calendar API."""

from __future__ import annotations

import os
import socket
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from supabase import Client, create_client

from app.main import app


def _has_local_supabase_env() -> bool:
    url = os.environ.get("SUPABASE_URL", "")
    return all(
        (
            url,
            os.environ.get("SUPABASE_ANON_KEY"),
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        )
    ) and ("127.0.0.1" in url or "localhost" in url)


def _can_reach_local_supabase() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 54321), timeout=1):
            return True
    except OSError:
        return False


skip_unless_local = pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase required.",
)


def _service_client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _create_user(label: str) -> dict[str, str]:
    svc = _service_client()
    email = f"cal-{label}-{uuid.uuid4()}@example.com"
    password = "Password123!"
    svc.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    login = create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"]
    ).auth.sign_in_with_password({"email": email, "password": password})
    return {
        "id": login.user.id,
        "access_token": login.session.access_token,
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def user() -> Iterator[dict[str, str]]:
    u = _create_user("u")
    try:
        yield u
    finally:
        _service_client().auth.admin.delete_user(u["id"])


def _auth(u: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {u['access_token']}"}


def _seed_scheduled(
    client: TestClient, user: dict[str, str], when: datetime, platforms: list[str]
) -> str:
    resp = client.post(
        "/api/posts",
        headers=_auth(user),
        json={
            "content_text": f"event at {when.isoformat()}",
            "status": "scheduled",
            "scheduled_at": when.isoformat(),
            "platforms": platforms,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    return resp.json()["id"]


@skip_unless_local
def test_calendar_returns_scheduled_events_in_range(
    client: TestClient, user: dict[str, str]
) -> None:
    inside = datetime.now(timezone.utc) + timedelta(days=2)
    outside = datetime.now(timezone.utc) + timedelta(days=30)
    _seed_scheduled(client, user, inside, ["x"])
    _seed_scheduled(client, user, outside, ["ig"])

    resp = client.get(
        "/api/calendar",
        headers=_auth(user),
        params={
            "from": (datetime.now(timezone.utc)).isoformat(),
            "to": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert len(body["events"]) == 1
    event = body["events"][0]
    assert event["status"] == "scheduled"
    assert event["platforms"] == ["x"]


@skip_unless_local
def test_calendar_filters_by_platform(
    client: TestClient, user: dict[str, str]
) -> None:
    when = datetime.now(timezone.utc) + timedelta(days=1)
    _seed_scheduled(client, user, when, ["x"])
    _seed_scheduled(client, user, when + timedelta(hours=2), ["ig"])

    resp = client.get(
        "/api/calendar",
        headers=_auth(user),
        params={
            "from": (datetime.now(timezone.utc)).isoformat(),
            "to": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "platforms": ["ig"],
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert len(body["events"]) == 1
    assert body["events"][0]["platforms"] == ["ig"]


@skip_unless_local
def test_calendar_rejects_reversed_range(
    client: TestClient, user: dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    resp = client.get(
        "/api/calendar",
        headers=_auth(user),
        params={"from": now.isoformat(), "to": (now - timedelta(days=1)).isoformat()},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@skip_unless_local
def test_calendar_includes_published_events(
    client: TestClient, user: dict[str, str]
) -> None:
    svc = _service_client()
    post_id = _seed_scheduled(
        client, user, datetime.now(timezone.utc) + timedelta(days=1), ["x"]
    )
    published_at = datetime.now(timezone.utc) - timedelta(hours=2)
    svc.table("posts").update(
        {
            "status": "published",
            "published_at": published_at.isoformat(),
            "scheduled_at": None,
        }
    ).eq("id", post_id).execute()

    resp = client.get(
        "/api/calendar",
        headers=_auth(user),
        params={
            "from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "to": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    events = resp.json()["events"]
    statuses = {e["status"] for e in events}
    assert "published" in statuses


@skip_unless_local
def test_calendar_requires_auth(client: TestClient) -> None:
    resp = client.get(
        "/api/calendar",
        params={
            "from": datetime.now(timezone.utc).isoformat(),
            "to": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
