"""ARCH-001/002: /internal/publish/flush のテスト."""

from __future__ import annotations

import os
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def token_env() -> Iterator[str]:
    token = "test-internal-token-123"
    original = os.environ.get("INTERNAL_API_TOKEN")
    os.environ["INTERNAL_API_TOKEN"] = token
    # config キャッシュを破棄
    get_settings.cache_clear()
    try:
        yield token
    finally:
        if original is None:
            os.environ.pop("INTERNAL_API_TOKEN", None)
        else:
            os.environ["INTERNAL_API_TOKEN"] = original
        get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_flush_requires_token(client: TestClient, token_env: str) -> None:
    resp = client.post("/internal/publish/flush")
    assert resp.status_code == 401


def test_flush_rejects_wrong_token(client: TestClient, token_env: str) -> None:
    resp = client.post(
        "/internal/publish/flush",
        headers={"X-Internal-Token": "wrong"},
    )
    assert resp.status_code == 401


def test_flush_returns_503_when_token_missing() -> None:
    # INTERNAL_API_TOKEN 未設定の場合は 503
    original = os.environ.pop("INTERNAL_API_TOKEN", None)
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        resp = client.post(
            "/internal/publish/flush",
            headers={"X-Internal-Token": "anything"},
        )
        assert resp.status_code == 503
    finally:
        if original is not None:
            os.environ["INTERNAL_API_TOKEN"] = original
        get_settings.cache_clear()


def test_flush_success_with_empty_queue(client: TestClient, token_env: str) -> None:
    with patch(
        "app.api.internal.run_flush",
        return_value={"processed": 0, "items": []},
    ) as mocked:
        resp = client.post(
            "/internal/publish/flush?limit=10",
            headers={"X-Internal-Token": token_env},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"processed": 0, "items": []}
    mocked.assert_called_once_with(limit=10, locked_by="gh-actions")


def test_flush_reports_items(client: TestClient, token_env: str) -> None:
    fake = {
        "processed": 2,
        "items": [
            {
                "queue_id": "q1",
                "post_id": "p1",
                "status": "success",
                "error": None,
                "terminal": None,
            },
            {
                "queue_id": "q2",
                "post_id": "p2",
                "status": "failed",
                "error": "api error",
                "terminal": False,
            },
        ],
    }
    with patch("app.api.internal.run_flush", return_value=fake):
        resp = client.post(
            "/internal/publish/flush",
            headers={"X-Internal-Token": token_env},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["status"] == "success"
    assert body["items"][1]["status"] == "failed"
