from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api import sns_accounts as sns_accounts_api
from app.core.security import CurrentUser, get_current_user
from app.main import app


class InMemoryAccountStore:
    def __init__(self) -> None:
        self.org_id = str(uuid4())
        self.other_org_id = str(uuid4())
        self.states: dict[str, dict[str, str]] = {}
        self.accounts: list[dict[str, object]] = []

    def get_default_org_id_for_user(self, user_id: str) -> str:
        return self.org_id

    def create_oauth_state(self, **payload: str) -> None:
        self.states[payload["state"]] = payload

    def consume_oauth_state(self, state: str, platform: str) -> dict[str, str]:
        row = self.states.pop(state, None)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state",
            )
        if row["platform"] != platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state does not match platform",
            )
        return row

    def upsert_sns_account(
        self,
        *,
        org_id: str,
        platform: str,
        handle: str,
        display_name: str | None,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> dict[str, object]:
        existing = next(
            (
                account
                for account in self.accounts
                if account["org_id"] == org_id
                and account["platform"] == platform
                and account["handle"] == handle
            ),
            None,
        )
        now = datetime.now(UTC)
        if existing is None:
            existing = {
                "id": uuid4(),
                "org_id": org_id,
                "platform": platform,
                "handle": handle,
                "display_name": display_name,
                "expires_at": expires_at,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
            self.accounts.append(existing)
        else:
            existing.update(
                {
                    "display_name": display_name,
                    "expires_at": expires_at,
                    "is_active": True,
                    "updated_at": now,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )
        return existing

    def list_sns_accounts_for_user(self, user_id: str) -> list[dict[str, object]]:
        return [
            account
            for account in self.accounts
            if account["org_id"] == self.org_id and account["is_active"] is True
        ]

    def deactivate_sns_account_for_user(self, user_id: str, account_id: str) -> None:
        for account in self.accounts:
            if str(account["id"]) == account_id and account["org_id"] == self.org_id:
                account["is_active"] = False
                account["updated_at"] = datetime.now(UTC)
                return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SNS account not found")


@pytest.fixture
def account_store(monkeypatch: pytest.MonkeyPatch) -> InMemoryAccountStore:
    store = InMemoryAccountStore()

    monkeypatch.setattr(
        sns_accounts_api,
        "get_settings",
        lambda: SimpleNamespace(oauth_redirect_base="http://localhost:8000"),
    )
    monkeypatch.setattr(
        sns_accounts_api.sns_account_service,
        "get_default_org_id_for_user",
        store.get_default_org_id_for_user,
    )
    monkeypatch.setattr(
        sns_accounts_api.sns_account_service,
        "create_oauth_state",
        store.create_oauth_state,
    )
    monkeypatch.setattr(
        sns_accounts_api.sns_account_service,
        "consume_oauth_state",
        store.consume_oauth_state,
    )
    monkeypatch.setattr(
        sns_accounts_api.sns_account_service,
        "upsert_sns_account",
        store.upsert_sns_account,
    )
    monkeypatch.setattr(
        sns_accounts_api.sns_account_service,
        "list_sns_accounts_for_user",
        store.list_sns_accounts_for_user,
    )
    monkeypatch.setattr(
        sns_accounts_api.sns_account_service,
        "deactivate_sns_account_for_user",
        store.deactivate_sns_account_for_user,
    )
    return store


@pytest.fixture
def authenticated_client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=str(uuid4()),
        email="tester@example.com",
        role="authenticated",
        access_token="test-token",
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client() -> TestClient:
    return TestClient(app)


def test_connect_x_returns_authorization_url(
    authenticated_client: TestClient,
    account_store: InMemoryAccountStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sns_accounts_api.oauth_x,
        "build_authorization_url",
        lambda callback_url: ("https://api.x.com/oauth/authorize?oauth_token=req-token", "req-token", "req-secret"),
    )

    response = authenticated_client.post("/api/sns-accounts/connect/x")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["authorization_url"].startswith("https://api.x.com/oauth/authorize")
    assert payload["state"] in account_store.states
    assert account_store.states[payload["state"]]["request_token"] == "req-token"


def test_connect_ig_returns_authorization_url(
    authenticated_client: TestClient,
    account_store: InMemoryAccountStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sns_accounts_api.oauth_ig,
        "build_authorization_url",
        lambda state, redirect_uri: f"https://facebook.com/dialog/oauth?state={state}",
    )

    response = authenticated_client.post("/api/sns-accounts/connect/ig")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["authorization_url"].startswith("https://facebook.com/dialog/oauth")
    assert payload["state"] in account_store.states
    assert account_store.states[payload["state"]]["platform"] == "ig"


def test_callback_x_rejects_state_mismatch(
    account_store: InMemoryAccountStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = "mismatch-state"
    account_store.states[state] = {
        "state": state,
        "platform": "ig",
        "org_id": account_store.org_id,
        "request_token": "req-token",
        "request_token_secret": "req-secret",
        "redirect_uri": "http://localhost:8000/api/sns-accounts/callback/x",
    }
    monkeypatch.setattr(
        sns_accounts_api.oauth_x,
        "exchange_code",
        lambda **_: pytest.fail("exchange_code must not be called on state mismatch"),
    )

    response = TestClient(app).get(
        "/api/sns-accounts/callback/x",
        params={
            "state": state,
            "oauth_token": "req-token",
            "oauth_verifier": "verifier",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_callback_ig_success_inserts_account_and_redirects(
    account_store: InMemoryAccountStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = "ig-success"
    account_store.states[state] = {
        "state": state,
        "platform": "ig",
        "org_id": account_store.org_id,
        "request_token": None,
        "request_token_secret": None,
        "redirect_uri": "http://localhost:8000/api/sns-accounts/callback/ig",
    }
    monkeypatch.setattr(
        sns_accounts_api.oauth_ig,
        "exchange_code",
        lambda code, redirect_uri: {
            "access_token": "ig-long-lived-token",
            "user_id": "1784",
            "handle": "joyfoundation_ig",
            "display_name": "Joy Foundation",
            "expires_at": datetime.now(UTC) + timedelta(days=60),
        },
    )

    response = TestClient(app).get(
        "/api/sns-accounts/callback/ig",
        params={"state": state, "code": "code-123"},
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_302_FOUND
    assert (
        response.headers["location"]
        == "http://localhost:8000/settings/sns?connected=ig&handle=joyfoundation_ig"
    )
    assert len(account_store.accounts) == 1
    assert account_store.accounts[0]["handle"] == "joyfoundation_ig"


def test_list_sns_accounts_returns_only_current_org(
    authenticated_client: TestClient,
    account_store: InMemoryAccountStore,
) -> None:
    now = datetime.now(UTC)
    account_store.accounts.extend(
        [
            {
                "id": uuid4(),
                "org_id": account_store.org_id,
                "platform": "x",
                "handle": "joy_x",
                "display_name": "Joy X",
                "expires_at": None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "access_token": "token",
                "refresh_token": None,
            },
            {
                "id": uuid4(),
                "org_id": account_store.other_org_id,
                "platform": "ig",
                "handle": "other_ig",
                "display_name": "Other",
                "expires_at": None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "access_token": "token",
                "refresh_token": None,
            },
        ]
    )

    response = authenticated_client.get("/api/sns-accounts")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert len(payload["accounts"]) == 1
    assert payload["accounts"][0]["handle"] == "joy_x"


def test_delete_sns_account_soft_deletes_and_hides_from_list(
    authenticated_client: TestClient,
    account_store: InMemoryAccountStore,
) -> None:
    now = datetime.now(UTC)
    account = {
        "id": uuid4(),
        "org_id": account_store.org_id,
        "platform": "x",
        "handle": "joy_x",
        "display_name": "Joy X",
        "expires_at": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "access_token": "token",
        "refresh_token": None,
    }
    account_store.accounts.append(account)

    delete_response = authenticated_client.delete(f"/api/sns-accounts/{account['id']}")
    list_response = authenticated_client.get("/api/sns-accounts")

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.json() == {"accounts": []}


def test_sns_accounts_requires_auth(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/api/sns-accounts")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
