import asyncio
import os
import socket
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from supabase import Client, create_client

from app.core.security import _extract_bearer_token, get_current_user
from app.main import app

LOCAL_SUPABASE_URL = "http://127.0.0.1:54321"


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


def _service_client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _cleanup_user(client: Client, user_id: str) -> None:
    client.auth.admin.delete_user(user_id)


def _create_test_user(client: Client, label: str) -> dict[str, str]:
    email = f"auth-{label}-{uuid.uuid4()}@example.com"
    password = "Password123!"
    created_user = client.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": f"Auth {label}"},
        }
    )
    return {
        "id": created_user.user.id,
        "email": email,
        "password": password,
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_extract_bearer_token_accepts_valid_header() -> None:
    assert _extract_bearer_token("Bearer token-123") == "token-123"


def test_extract_bearer_token_rejects_invalid_header() -> None:
    with pytest.raises(Exception) as exc_info:
        _extract_bearer_token("Basic token-123")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_rejects_missing_authorization() -> None:
    with pytest.raises(Exception) as exc_info:
        asyncio.run(get_current_user())

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_signup_creates_user_and_profile(client: TestClient) -> None:
    assert os.environ["SUPABASE_URL"].rstrip("/") == LOCAL_SUPABASE_URL
    service_client = _service_client()
    email = f"signup-{uuid.uuid4()}@example.com"
    created_user_id: str | None = None

    try:
        response = client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": "Password123!",
                "display_name": "Signup Test",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        created_user_id = payload["user"]["id"]
        assert payload["user"]["email"] == email
        assert payload["user"]["display_name"] == "Signup Test"
        assert payload["token_type"] == "bearer"
        assert payload["access_token"]
        assert payload["refresh_token"]

        profile_rows = (
            service_client.table("users")
            .select("id,email,display_name,default_org_id")
            .eq("id", created_user_id)
            .limit(1)
            .execute()
            .data
        )
        assert profile_rows
        assert profile_rows[0]["email"] == email
        assert profile_rows[0]["default_org_id"] is not None
    finally:
        if created_user_id:
            _cleanup_user(service_client, created_user_id)


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_signup_rejects_duplicate_email(client: TestClient) -> None:
    service_client = _service_client()
    email = f"duplicate-{uuid.uuid4()}@example.com"
    created_user_id: str | None = None

    try:
        first_response = client.post(
            "/api/auth/signup",
            json={"email": email, "password": "Password123!"},
        )
        assert first_response.status_code == status.HTTP_201_CREATED
        created_user_id = first_response.json()["user"]["id"]

        second_response = client.post(
            "/api/auth/signup",
            json={"email": email, "password": "Password123!"},
        )

        assert second_response.status_code in {
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
        }
    finally:
        if created_user_id:
            _cleanup_user(service_client, created_user_id)


def test_signup_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/signup",
        json={"email": "short@example.com", "password": "short"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_login_returns_session(client: TestClient) -> None:
    service_client = _service_client()
    user = _create_test_user(service_client, "login")

    try:
        response = client.post(
            "/api/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["user"]["id"] == user["id"]
        assert payload["access_token"]
        assert payload["refresh_token"]
    finally:
        _cleanup_user(service_client, user["id"])


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_login_rejects_wrong_password(client: TestClient) -> None:
    service_client = _service_client()
    user = _create_test_user(service_client, "wrong-password")

    try:
        response = client.post(
            "/api/auth/login",
            json={"email": user["email"], "password": "WrongPassword123!"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    finally:
        _cleanup_user(service_client, user["id"])


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_rejects_invalid_bearer_token(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_me_returns_profile_for_valid_bearer(client: TestClient) -> None:
    service_client = _service_client()
    user = _create_test_user(service_client, "me")

    try:
        login_response = client.post(
            "/api/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.json()["access_token"]

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["id"] == user["id"]
        assert payload["email"] == user["email"]
        assert payload["default_org_id"] is not None
    finally:
        _cleanup_user(service_client, user["id"])


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_logout_returns_message_for_valid_bearer(client: TestClient) -> None:
    service_client = _service_client()
    user = _create_test_user(service_client, "logout")

    try:
        login_response = client.post(
            "/api/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.json()["access_token"]

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Logged out"}
    finally:
        _cleanup_user(service_client, user["id"])


@pytest.mark.skipif(
    not _has_local_supabase_env() or not _can_reach_local_supabase(),
    reason="Local Supabase environment variables are not configured or the local Supabase API is unreachable.",
)
def test_refresh_returns_new_session(client: TestClient) -> None:
    service_client = _service_client()
    user = _create_test_user(service_client, "refresh")

    try:
        login_response = client.post(
            "/api/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert login_response.status_code == status.HTTP_200_OK
        refresh_token = login_response.json()["refresh_token"]

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["user"]["id"] == user["id"]
        assert payload["access_token"]
        assert payload["refresh_token"]
    finally:
        _cleanup_user(service_client, user["id"])
