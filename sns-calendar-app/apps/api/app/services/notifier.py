"""投稿結果の通知サービス (WEB-023 / WEB-027 / ARCH-003).

送信チャネル:
- Email (SMTP_SSL) — WEB-023
- DB 永続化 — WEB-027 / ARCH-003

DB への INSERT は Supabase Realtime の postgres_changes 経由で Web クライアントに
届く（ARCH-003 で Redis PubSub + WebSocket を撤廃）。

すべてのチャネルは失敗しても warning ログで握り潰し、呼び出し側の処理フロー
（publish_post）を止めない。
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

PostSummary = dict[str, list[dict[str, Any]]]


class EmailChannel:
    """メール送信チャネル。Resend API を優先し、未設定なら SMTP_SSL にフォールバック.

    ARCH-005: RESEND_API_KEY が設定されていれば Resend API で送信。
    設定がなければ従来どおり smtplib SMTP_SSL で送信する。
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, *, to: str, subject: str, body: str) -> bool:
        settings = self._settings
        if settings.resend_api_key and settings.smtp_from_address:
            return self._send_via_resend(to=to, subject=subject, body=body)

        if not (settings.smtp_host and settings.smtp_from_address):
            logger.warning("No email backend configured; skipping email to %s", to)
            return False

        return self._send_via_smtp(to=to, subject=subject, body=body)

    def _send_via_resend(self, *, to: str, subject: str, body: str) -> bool:
        settings = self._settings
        try:
            import resend  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("resend package not installed; skipping email to %s", to)
            return False

        assert settings.resend_api_key is not None
        assert settings.smtp_from_address is not None
        resend.api_key = settings.resend_api_key.get_secret_value()
        try:
            resend.Emails.send(
                {
                    "from": settings.smtp_from_address,
                    "to": [to],
                    "subject": subject,
                    "text": body,
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to send email via Resend to %s: %s", to, exc)
            return False
        return True

    def _send_via_smtp(self, *, to: str, subject: str, body: str) -> bool:
        settings = self._settings
        message = EmailMessage()
        message["From"] = settings.smtp_from_address
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
                if settings.smtp_user and settings.smtp_password is not None:
                    smtp.login(
                        settings.smtp_user,
                        settings.smtp_password.get_secret_value(),
                    )
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning("Failed to send email via SMTP to %s: %s", to, exc)
            return False
        return True


def _build_subject(summary: PostSummary) -> str:
    success_count = len(summary.get("success") or [])
    failed_count = len(summary.get("failed") or [])
    if failed_count and success_count:
        return "[SNS Calendar] 投稿結果: 一部失敗"
    if failed_count:
        return "[SNS Calendar] 投稿結果: 失敗"
    return "[SNS Calendar] 投稿結果: 成功"


def _build_body(post_id: str, summary: PostSummary) -> str:
    lines: list[str] = [f"投稿 ID: {post_id}", ""]
    success = summary.get("success") or []
    failed = summary.get("failed") or []

    if success:
        lines.append("[成功]")
        for item in success:
            platform = item.get("platform") or "unknown"
            reference = item.get("platform_post_id") or "-"
            lines.append(f"- {platform} に投稿しました: {reference}")
        lines.append("")

    if failed:
        lines.append("[失敗]")
        for item in failed:
            platform = item.get("platform") or "unknown"
            error = item.get("error") or "不明なエラー"
            lines.append(f"- {platform} 投稿失敗: {error}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _classify(summary: PostSummary) -> str:
    success_count = len(summary.get("success") or [])
    failed_count = len(summary.get("failed") or [])
    if failed_count and success_count:
        return "post_partial"
    if failed_count:
        return "post_failed"
    return "post_published"


def _persist_notification(
    *,
    user_id: str,
    post_id: str,
    kind: str,
    title: str,
    body: str,
) -> dict[str, Any] | None:
    """`notifications` テーブルに INSERT。失敗は warning で握り潰して None を返す."""
    try:
        from app.core.supabase import get_supabase_client

        client = get_supabase_client()
        response = (
            client.table("notifications")
            .insert(
                {
                    "user_id": user_id,
                    "kind": kind,
                    "title": title,
                    "body": body,
                    "related_post_id": post_id,
                }
            )
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "notifications insert failed for user_id=%s post_id=%s: %s",
            user_id,
            post_id,
            exc,
        )
        return None


def notify_post_result(
    *,
    post_id: str,
    owner_email: str,
    summary: PostSummary,
    user_id: str | None = None,
    channel: EmailChannel | None = None,
) -> None:
    """publish_post の結果 summary を owner に通知する (mail + DB + WS).

    summary は ``{"success": [...], "failed": [...]}`` 形式。各チャネルの失敗は
    warning ログで握り潰し、例外を伝播しない。
    """
    subject = _build_subject(summary)
    body = _build_body(post_id, summary)

    if owner_email:
        try:
            active_channel = channel or EmailChannel(get_settings())
            active_channel.send(to=owner_email, subject=subject, body=body)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "notify_post_result swallowed email error for post_id=%s: %s",
                post_id,
                exc,
            )
    else:
        logger.warning(
            "notify_post_result: owner_email is empty for post_id=%s", post_id
        )

    if user_id:
        kind = _classify(summary)
        # INSERT は Supabase Realtime で自動的にクライアントへ配信される。
        _persist_notification(
            user_id=user_id,
            post_id=post_id,
            kind=kind,
            title=subject,
            body=body,
        )
