"""投稿結果のメール通知サービス (WEB-023).

SMTP_SSL 経由で送信する薄いラッパー。設定未設定・送信失敗はすべて
warning ログで握り潰し、呼び出し側の処理フローを止めない。
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
    """SMTP_SSL でメールを送信する通知チャネル."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, *, to: str, subject: str, body: str) -> bool:
        settings = self._settings
        if not (settings.smtp_host and settings.smtp_from_address):
            logger.warning("SMTP is not configured; skipping email to %s", to)
            return False

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
            logger.warning("Failed to send email to %s: %s", to, exc)
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


def notify_post_result(
    *,
    post_id: str,
    owner_email: str,
    summary: PostSummary,
    channel: EmailChannel | None = None,
) -> None:
    """publish_post の結果 summary を owner にメール通知する.

    summary は ``{"success": [...], "failed": [...]}`` 形式の dict を想定する.
    送信失敗は warning ログのみで握り潰し、例外を伝播しない.
    """
    if not owner_email:
        logger.warning("notify_post_result: owner_email is empty for post_id=%s", post_id)
        return

    try:
        active_channel = channel or EmailChannel(get_settings())
        subject = _build_subject(summary)
        body = _build_body(post_id, summary)
        active_channel.send(to=owner_email, subject=subject, body=body)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "notify_post_result swallowed error for post_id=%s: %s",
            post_id,
            exc,
        )
