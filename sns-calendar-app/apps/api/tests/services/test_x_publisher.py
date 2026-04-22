from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from app.services.publisher.x_publisher import MEDIA_UPLOAD_URL, TWEET_CREATE_URL, XPublisher


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int,
        json_data: Any = None,
        text: str = "",
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        if text:
            self.text = text
        elif json_data is not None:
            self.text = json.dumps(json_data)
        else:
            self.text = ""
        self.content = content
        self.headers = headers or {}

    def json(self) -> Any:
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


def build_publisher() -> XPublisher:
    return XPublisher(consumer_key="consumer-key", consumer_secret="consumer-secret")


def build_account(token: str = "user-token:user-secret") -> dict[str, str]:
    return {"access_token": token}


def test_publish_success_with_media_and_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = build_publisher()
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, timeout: int) -> DummyResponse:
        assert url == "https://cdn.example.com/image.jpg"
        assert timeout == 30
        return DummyResponse(
            status_code=200,
            content=b"img",
            headers={"Content-Type": "image/jpeg"},
        )

    def fake_post(url: str, **kwargs: Any) -> DummyResponse:
        calls.append({"url": url, **kwargs})
        if url == MEDIA_UPLOAD_URL:
            return DummyResponse(status_code=200, json_data={"media_id_string": "media-1"})
        if url == TWEET_CREATE_URL:
            return DummyResponse(status_code=201, json_data={"data": {"id": "tweet-1"}})
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.services.publisher.x_publisher.requests.get", fake_get)
    monkeypatch.setattr("app.services.publisher.x_publisher.requests.post", fake_post)

    result = publisher.publish(
        text="hello",
        image_urls=["https://cdn.example.com/image.jpg"],
        account=build_account(),
        options={"reply_to": "parent-1"},
    )

    assert result.success is True
    assert result.platform_post_id == "tweet-1"
    tweet_call = calls[-1]
    assert tweet_call["json"]["media"]["media_ids"] == ["media-1"]
    assert tweet_call["json"]["reply"]["in_reply_to_tweet_id"] == "parent-1"


def test_publish_success_without_media(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = build_publisher()
    calls: list[str] = []

    def fake_post(url: str, **kwargs: Any) -> DummyResponse:
        calls.append(url)
        return DummyResponse(status_code=200, json_data={"data": {"id": "tweet-2"}})

    monkeypatch.setattr("app.services.publisher.x_publisher.requests.post", fake_post)

    result = publisher.publish(
        text="hello",
        image_urls=[],
        account=build_account(),
    )

    assert result.success is True
    assert result.platform_post_id == "tweet-2"
    assert calls == [TWEET_CREATE_URL]


def test_publish_skips_media_upload_failure_and_still_posts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publisher = build_publisher()
    tweet_payloads: list[dict[str, Any]] = []

    monkeypatch.setattr(
        "app.services.publisher.x_publisher.requests.get",
        lambda url, timeout: DummyResponse(
            status_code=200,
            content=b"img",
            headers={"Content-Type": "image/jpeg"},
        ),
    )

    def fake_post(url: str, **kwargs: Any) -> DummyResponse:
        if url == MEDIA_UPLOAD_URL:
            return DummyResponse(status_code=500, json_data={"detail": "bad media"})
        tweet_payloads.append(kwargs["json"])
        return DummyResponse(status_code=200, json_data={"data": {"id": "tweet-3"}})

    monkeypatch.setattr("app.services.publisher.x_publisher.requests.post", fake_post)

    result = publisher.publish(
        text="hello",
        image_urls=["https://cdn.example.com/image.jpg"],
        account=build_account(),
    )

    assert result.success is True
    assert result.platform_post_id == "tweet-3"
    assert "media" not in tweet_payloads[0]


def test_publish_returns_failure_for_401(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = build_publisher()
    monkeypatch.setattr(
        "app.services.publisher.x_publisher.requests.post",
        lambda url, **kwargs: DummyResponse(
            status_code=401,
            json_data={"detail": "unauthorized"},
        ),
    )

    result = publisher.publish(
        text="hello",
        image_urls=[],
        account=build_account(),
    )

    assert result.success is False
    assert "401" in (result.error_message or "")


def test_publish_returns_failure_for_500(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = build_publisher()
    monkeypatch.setattr(
        "app.services.publisher.x_publisher.requests.post",
        lambda url, **kwargs: DummyResponse(
            status_code=500,
            json_data={"detail": "server error"},
        ),
    )

    result = publisher.publish(
        text="hello",
        image_urls=[],
        account=build_account(),
    )

    assert result.success is False
    assert "500" in (result.error_message or "")


def test_publish_returns_failure_for_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = build_publisher()

    def raise_connection_error(url: str, **kwargs: Any) -> DummyResponse:
        raise requests.ConnectionError("network down")

    monkeypatch.setattr("app.services.publisher.x_publisher.requests.post", raise_connection_error)

    result = publisher.publish(
        text="hello",
        image_urls=[],
        account=build_account(),
    )

    assert result.success is False
    assert "network down" in (result.error_message or "")


def test_publish_returns_failure_when_access_token_missing() -> None:
    publisher = build_publisher()

    result = publisher.publish(
        text="hello",
        image_urls=[],
        account={},
    )

    assert result.success is False
    assert result.error_message == "X account access token is missing"


def test_publish_returns_failure_for_malformed_access_token() -> None:
    publisher = build_publisher()

    result = publisher.publish(
        text="hello",
        image_urls=[],
        account=build_account("broken-token"),
    )

    assert result.success is False
    assert result.error_message == "X account access token is malformed"
