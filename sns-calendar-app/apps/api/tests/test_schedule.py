"""End-to-end tests for WEB-012 schedule/unschedule/reschedule/publish-now."""

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
    email = f"sched-{label}-{uuid.uuid4()}@example.com"
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
    u = _create_user("user")
    try:
        yield u
    finally:
        _service_client().auth.admin.delete_user(u["id"])


def _auth(u: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {u['access_token']}"}


def _create_draft(client: TestClient, user: dict[str, str]) -> dict[str, object]:
    resp = client.post(
        "/api/posts",
        headers=_auth(user),
        json={"content_text": "schedule test"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    return resp.json()


@skip_unless_local
def test_schedule_draft_post(client: TestClient, user: dict[str, str]) -> None:
    post = _create_draft(client, user)
    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/api/posts/{post['id']}/schedule",
        headers=_auth(user),
        json={"scheduled_at": scheduled_at},
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == "scheduled"
    assert body["scheduled_at"] is not None


@skip_unless_local
def test_schedule_conflict_on_published_post(
    client: TestClient, user: dict[str, str]
) -> None:
    post = _create_draft(client, user)
    svc = _service_client()
    svc.table("posts").update(
        {
            "status": "published",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", post["id"]).execute()

    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/api/posts/{post['id']}/schedule",
        headers=_auth(user),
        json={"scheduled_at": scheduled_at},
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


@skip_unless_local
def test_reschedule_scheduled_post(client: TestClient, user: dict[str, str]) -> None:
    post = _create_draft(client, user)
    first = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    client.post(
        f"/api/posts/{post['id']}/schedule",
        headers=_auth(user),
        json={"scheduled_at": first},
    )
    second = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    resp = client.post(
        f"/api/posts/{post['id']}/reschedule",
        headers=_auth(user),
        json={"scheduled_at": second},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["scheduled_at"] is not None


@skip_unless_local
def test_reschedule_refuses_draft(client: TestClient, user: dict[str, str]) -> None:
    post = _create_draft(client, user)
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/api/posts/{post['id']}/reschedule",
        headers=_auth(user),
        json={"scheduled_at": future},
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


@skip_unless_local
def test_unschedule_reverts_to_draft(client: TestClient, user: dict[str, str]) -> None:
    post = _create_draft(client, user)
    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    client.post(
        f"/api/posts/{post['id']}/schedule",
        headers=_auth(user),
        json={"scheduled_at": scheduled_at},
    )
    resp = client.post(
        f"/api/posts/{post['id']}/unschedule",
        headers=_auth(user),
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == "draft"
    assert body["scheduled_at"] is None


@skip_unless_local
def test_unschedule_refuses_draft(client: TestClient, user: dict[str, str]) -> None:
    post = _create_draft(client, user)
    resp = client.post(
        f"/api/posts/{post['id']}/unschedule",
        headers=_auth(user),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


@skip_unless_local
def test_publish_now_schedules_immediately(
    client: TestClient, user: dict[str, str]
) -> None:
    post = _create_draft(client, user)
    resp = client.post(
        f"/api/posts/{post['id']}/publish-now",
        headers=_auth(user),
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == "scheduled"
    # scheduled_at should be roughly now (within 60s)
    scheduled_at = datetime.fromisoformat(body["scheduled_at"])
    delta = (datetime.now(timezone.utc) - scheduled_at).total_seconds()
    assert abs(delta) < 60


@skip_unless_local
def test_publish_now_refuses_published(
    client: TestClient, user: dict[str, str]
) -> None:
    post = _create_draft(client, user)
    svc = _service_client()
    svc.table("posts").update(
        {
            "status": "published",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", post["id"]).execute()
    resp = client.post(
        f"/api/posts/{post['id']}/publish-now",
        headers=_auth(user),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


@skip_unless_local
def test_schedule_requires_authentication(client: TestClient) -> None:
    resp = client.post(
        "/api/posts/00000000-0000-0000-0000-000000000000/schedule",
        json={"scheduled_at": datetime.now(timezone.utc).isoformat()},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
