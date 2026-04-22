from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

import pytest

from app.config import Settings
from app.services.notifier import EmailChannel, notify_post_result


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": 465,
        "SMTP_USER": "sender@example.com",
        "SMTP_PASSWORD": "s3cret-should-not-be-logged",
        "SMTP_FROM_ADDRESS": "sender@example.com",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


class _FakeSMTP:
    def __init__(self, host: str, port: int, *args: Any, **kwargs: Any) -> None:
        self.host = host
        self.port = port
        self.sent_messages: list[EmailMessage] = []
        self.logged_in_with: tuple[str, str] | None = None
        self.send_exc: Exception | None = None
        self.__class__.last_instance = self  # type: ignore[attr-defined]

    def __enter__(self) -> _FakeSMTP:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def login(self, user: str, password: str) -> None:
        self.logged_in_with = (user, password)

    def send_message(self, message: EmailMessage) -> None:
        if self.send_exc is not None:
            raise self.send_exc
        self.sent_messages.append(message)


def _install_fake_smtp(
    monkeypatch: pytest.MonkeyPatch,
    *,
    send_exc: Exception | None = None,
    connect_exc: Exception | None = None,
) -> type[_FakeSMTP]:
    def factory(host: str, port: int, *args: Any, **kwargs: Any) -> _FakeSMTP:
        if connect_exc is not None:
            raise connect_exc
        instance = _FakeSMTP(host, port)
        instance.send_exc = send_exc
        return instance

    monkeypatch.setattr(smtplib, "SMTP_SSL", factory)
    return _FakeSMTP


def test_email_channel_send_uses_smtp_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_smtp(monkeypatch)
    channel = EmailChannel(_settings())

    sent = channel.send(
        to="owner@example.com",
        subject="件名",
        body="本文テスト",
    )

    instance = _FakeSMTP.last_instance  # type: ignore[attr-defined]
    assert sent is True
    assert instance.host == "smtp.example.com"
    assert instance.port == 465
    assert instance.logged_in_with == ("sender@example.com", "s3cret-should-not-be-logged")
    assert len(instance.sent_messages) == 1
    message = instance.sent_messages[0]
    assert message["To"] == "owner@example.com"
    assert message["Subject"] == "件名"
    assert "本文テスト" in message.get_content()


def test_email_channel_returns_false_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _fail_if_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("SMTP_SSL should not be called when unconfigured")

    monkeypatch.setattr(smtplib, "SMTP_SSL", _fail_if_called)

    channel = EmailChannel(_settings(SMTP_HOST=None, SMTP_FROM_ADDRESS=None))

    with caplog.at_level(logging.WARNING, logger="app.services.notifier"):
        sent = channel.send(to="owner@example.com", subject="s", body="b")

    assert sent is False
    assert any(
        "No email backend configured" in record.message for record in caplog.records
    )


def test_email_channel_handles_connection_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_fake_smtp(monkeypatch, connect_exc=OSError("dns failure"))
    channel = EmailChannel(_settings())

    with caplog.at_level(logging.WARNING, logger="app.services.notifier"):
        sent = channel.send(to="owner@example.com", subject="s", body="b")

    assert sent is False
    assert any("Failed to send email" in record.message for record in caplog.records)


def test_email_channel_does_not_leak_password_in_logs(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_fake_smtp(
        monkeypatch,
        send_exc=smtplib.SMTPException("relay rejected"),
    )
    channel = EmailChannel(_settings())

    with caplog.at_level(logging.DEBUG, logger="app.services.notifier"):
        sent = channel.send(to="owner@example.com", subject="s", body="b")

    assert sent is False
    for record in caplog.records:
        assert "s3cret-should-not-be-logged" not in record.getMessage()


def test_notify_post_result_formats_mixed_body(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_smtp(monkeypatch)

    notify_post_result(
        post_id="post-123",
        owner_email="owner@example.com",
        summary={
            "success": [
                {"platform": "x", "platform_post_id": "111222333"},
            ],
            "failed": [
                {"platform": "instagram", "error": "token expired"},
            ],
        },
        channel=EmailChannel(_settings()),
    )

    instance = _FakeSMTP.last_instance  # type: ignore[attr-defined]
    assert len(instance.sent_messages) == 1
    message = instance.sent_messages[0]
    assert message["Subject"] == "[SNS Calendar] 投稿結果: 一部失敗"
    content = message.get_content()
    assert "投稿 ID: post-123" in content
    assert "x に投稿しました: 111222333" in content
    assert "instagram 投稿失敗: token expired" in content


def test_notify_post_result_success_only_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_smtp(monkeypatch)

    notify_post_result(
        post_id="post-42",
        owner_email="owner@example.com",
        summary={
            "success": [
                {"platform": "x", "platform_post_id": "abc"},
            ],
            "failed": [],
        },
        channel=EmailChannel(_settings()),
    )

    instance = _FakeSMTP.last_instance  # type: ignore[attr-defined]
    assert instance.sent_messages[0]["Subject"] == "[SNS Calendar] 投稿結果: 成功"


def test_notify_post_result_skips_when_owner_email_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail_if_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("SMTP should not be contacted when email is empty")

    monkeypatch.setattr(smtplib, "SMTP_SSL", _fail_if_called)

    notify_post_result(
        post_id="post-42",
        owner_email="",
        summary={"success": [], "failed": []},
        channel=EmailChannel(_settings()),
    )


def test_notify_post_result_swallows_send_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_fake_smtp(
        monkeypatch,
        send_exc=smtplib.SMTPRecipientsRefused({"owner@example.com": (550, b"no mailbox")}),
    )

    with caplog.at_level(logging.WARNING, logger="app.services.notifier"):
        notify_post_result(
            post_id="post-99",
            owner_email="owner@example.com",
            summary={
                "success": [],
                "failed": [{"platform": "x", "error": "boom"}],
            },
            channel=EmailChannel(_settings()),
        )

    assert any("Failed to send email" in record.message for record in caplog.records)


# ARCH-005: Resend API backend tests ------------------------------------------


def _install_fake_resend(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """sys.modules に擬似 resend モジュールを差し込む."""
    import sys
    import types

    state: dict[str, Any] = {"api_key": None, "payload": None}

    class _Emails:
        @staticmethod
        def send(payload: dict[str, Any]) -> dict[str, Any]:
            state["payload"] = payload
            return {"id": "rsnd_test_123"}

    # モジュールレベル属性 api_key への代入を state に反映する
    class _ModuleWrapper(types.ModuleType):
        @property
        def api_key(self) -> Any:  # type: ignore[override]
            return state["api_key"]

        @api_key.setter
        def api_key(self, value: str) -> None:
            state["api_key"] = value

    wrapper = _ModuleWrapper("resend")
    wrapper.Emails = _Emails  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "resend", wrapper)
    return state


def test_email_channel_uses_resend_when_key_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _install_fake_resend(monkeypatch)

    channel = EmailChannel(
        _settings(RESEND_API_KEY="resend-test-key", SMTP_HOST=None)
    )

    sent = channel.send(
        to="owner@example.com",
        subject="件名",
        body="本文テスト",
    )

    assert sent is True
    assert state["api_key"] == "resend-test-key"
    payload = state["payload"]
    assert payload is not None
    assert payload["from"] == "sender@example.com"
    assert payload["to"] == ["owner@example.com"]
    assert payload["subject"] == "件名"
    assert payload["text"] == "本文テスト"


def test_email_channel_falls_back_to_smtp_without_resend_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_smtp(monkeypatch)
    channel = EmailChannel(_settings())  # RESEND_API_KEY 未設定

    sent = channel.send(
        to="owner@example.com",
        subject="件名",
        body="本文",
    )

    assert sent is True
    instance = _FakeSMTP.last_instance  # type: ignore[attr-defined]
    assert instance.host == "smtp.example.com"
