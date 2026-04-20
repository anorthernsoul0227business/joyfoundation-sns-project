"""End-to-end tests for the post CRUD API (WEB-011)."""

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


def _create_test_user(label: str) -> dict[str, str]:
    svc = _service_client()
    email = f"posts-{label}-{uuid.uuid4()}@example.com"
    password = "Password123!"
    created_user = svc.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": f"Posts {label}"},
        }
    )
    user_id = created_user.user.id
    login = create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"]
    ).auth.sign_in_with_password({"email": email, "password": password})
    return {
        "id": user_id,
        "email": email,
        "access_token": login.session.access_token,
        "refresh_token": login.session.refresh_token,
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def primary_user() -> Iterator[dict[str, str]]:
    user = _create_test_user("primary")
    try:
        yield user
    finally:
        _service_client().auth.admin.delete_user(user["id"])


@pytest.fixture
def other_user() -> Iterator[dict[str, str]]:
    user = _create_test_user("other")
    try:
        yield user
    finally:
        _service_client().auth.admin.delete_user(user["id"])


def _auth_headers(user: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {user['access_token']}"}


@skip_unless_local
def test_create_post_draft(client: TestClient, primary_user: dict[str, str]) -> None:
    response = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={
            "content_text": "Hello world",
            "platforms": ["x"],
            "media": [{"storage_path": "tmp/a.png", "mime_type": "image/png"}],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "draft"
    assert body["user_id"] == primary_user["id"]
    assert body["content_text"] == "Hello world"
    assert len(body["targets"]) == 1
    assert body["targets"][0]["platform"] == "x"
    assert len(body["media"]) == 1
    assert body["media"][0]["storage_path"] == "tmp/a.png"


@skip_unless_local
def test_create_scheduled_post_requires_scheduled_at(
    client: TestClient, primary_user: dict[str, str]
) -> None:
    response = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={"content_text": "must have scheduled_at", "status": "scheduled"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@skip_unless_local
def test_create_scheduled_post_success(
    client: TestClient, primary_user: dict[str, str]
) -> None:
    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={
            "content_text": "scheduled",
            "status": "scheduled",
            "scheduled_at": scheduled_at,
            "platforms": ["x", "ig"],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["scheduled_at"] is not None
    assert {t["platform"] for t in body["targets"]} == {"x", "ig"}


@skip_unless_local
def test_list_posts_only_returns_own_org(
    client: TestClient,
    primary_user: dict[str, str],
    other_user: dict[str, str],
) -> None:
    # primary creates one post
    client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={"content_text": "primary only"},
    )
    # other creates a different one
    client.post(
        "/api/posts",
        headers=_auth_headers(other_user),
        json={"content_text": "other only"},
    )
    # primary should see only their own post
    response = client.get("/api/posts", headers=_auth_headers(primary_user))
    assert response.status_code == status.HTTP_200_OK
    bodies = [p["content_text"] for p in response.json()["items"]]
    assert "primary only" in bodies
    assert "other only" not in bodies


@skip_unless_local
def test_get_post_by_id(client: TestClient, primary_user: dict[str, str]) -> None:
    created = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={"content_text": "fetch me"},
    ).json()
    post_id = created["id"]

    response = client.get(f"/api/posts/{post_id}", headers=_auth_headers(primary_user))
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == post_id


@skip_unless_local
def test_get_post_from_other_org_returns_404(
    client: TestClient,
    primary_user: dict[str, str],
    other_user: dict[str, str],
) -> None:
    created = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={"content_text": "private"},
    ).json()
    response = client.get(
        f"/api/posts/{created['id']}", headers=_auth_headers(other_user)
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@skip_unless_local
def test_update_post(client: TestClient, primary_user: dict[str, str]) -> None:
    created = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={"content_text": "before"},
    ).json()
    response = client.patch(
        f"/api/posts/{created['id']}",
        headers=_auth_headers(primary_user),
        json={"content_text": "after"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["content_text"] == "after"


@skip_unless_local
def test_update_to_scheduled_requires_scheduled_at(
    client: TestClient, primary_user: dict[str, str]
) -> None:
    created = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={"content_text": "draft"},
    ).json()
    response = client.patch(
        f"/api/posts/{created['id']}",
        headers=_auth_headers(primary_user),
        json={"status": "scheduled"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@skip_unless_local
def test_delete_post(client: TestClient, primary_user: dict[str, str]) -> None:
    created = client.post(
        "/api/posts",
        headers=_auth_headers(primary_user),
        json={"content_text": "to delete"},
    ).json()
    response = client.delete(
        f"/api/posts/{created['id']}", headers=_auth_headers(primary_user)
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Confirm gone
    follow = client.get(f"/api/posts/{created['id']}", headers=_auth_headers(primary_user))
    assert follow.status_code == status.HTTP_404_NOT_FOUND


@skip_unless_local
def test_unauthenticated_requests_rejected(client: TestClient) -> None:
    assert client.get("/api/posts").status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        client.post("/api/posts", json={"content_text": "nope"}).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
