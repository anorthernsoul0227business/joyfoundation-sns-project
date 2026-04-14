#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNS投稿通知モジュール（チャネル抽象化版）

使い方:
    from notifier import build_default_notifier

    notifier = build_default_notifier()
    notifier.notify_success(
        platform='Instagram',
        caption='【仙台で開催中】...',
        post_url='https://www.instagram.com/p/xxx/',
        image_url='https://...',
    )
    notifier.notify_failure(
        platform='Instagram',
        caption='【仙台で...】',
        error='API認証エラー',
    )

設計:
    Notifier: 複数チャネルのファサード
    NotificationChannel: 抽象基底クラス
    GmailChannel: Gmail SMTPによるメール送信
    LineChannel (未実装): 将来追加予定
    FcmChannel (未実装): アプリリリース後に追加予定

.env に必要なキー:
    NOTIFY_GMAIL_USER        - 送信元Gmailアドレス
    NOTIFY_GMAIL_APP_PASSWORD - Gmailアプリパスワード（16桁）
    NOTIFY_GMAIL_TO          - 送信先メール（カンマ区切り複数可）
    NOTIFY_ENABLED           - 通知全体の有効/無効 (true/false, default: true)
"""

import os
import ssl
import smtplib
import logging
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """通知チャネルの抽象基底クラス"""

    @abstractmethod
    def send(
        self,
        title: str,
        body_text: str,
        body_html: Optional[str] = None,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> bool:
        """通知を送信。成功時True、失敗時False。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class GmailChannel(NotificationChannel):
    """Gmail SMTPを使った通知チャネル"""

    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 465

    def __init__(
        self,
        sender: str,
        app_password: str,
        recipients: List[str],
        display_name: str = 'SNS Auto Poster',
    ):
        self.sender = sender
        self.app_password = app_password
        self.recipients = [r.strip() for r in recipients if r and r.strip()]
        self.display_name = display_name

    @property
    def name(self) -> str:
        return 'gmail'

    def send(
        self,
        title: str,
        body_text: str,
        body_html: Optional[str] = None,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> bool:
        if not self.recipients:
            logger.warning("GmailChannel: 送信先が空のためスキップ")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = title
        msg['From'] = f"{self.display_name} <{self.sender}>"
        msg['To'] = ', '.join(self.recipients)

        # テキスト版
        text_parts = [body_text]
        if link:
            text_parts.append('')
            text_parts.append(f'投稿URL: {link}')
        if image_url:
            text_parts.append(f'画像: {image_url}')
        text_content = '\n'.join(text_parts)
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

        # HTML版（指定なければ自動生成）
        if body_html is None:
            body_html = self._build_html(body_text, link, image_url)
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT, context=context, timeout=30) as server:
                server.login(self.sender, self.app_password)
                server.send_message(msg)
            logger.info(f"Gmail通知送信成功: {title} → {len(self.recipients)}件")
            return True
        except Exception as e:
            logger.error(f"Gmail通知送信失敗: {e}")
            return False

    @staticmethod
    def _build_html(body_text: str, link: Optional[str], image_url: Optional[str]) -> str:
        # 改行をHTML化
        body_html_lines = body_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        body_html_lines = body_html_lines.replace('\n', '<br>')

        parts = [
            '<html><body style="font-family: -apple-system, sans-serif; color: #222;">',
            f'<div style="white-space: pre-wrap;">{body_html_lines}</div>',
        ]
        if link:
            parts.append(
                f'<p style="margin-top: 16px;">'
                f'<a href="{link}" style="background: #0095f6; color: #fff; padding: 10px 20px; '
                f'text-decoration: none; border-radius: 6px; display: inline-block;">投稿を開く</a>'
                f'</p>'
            )
        if image_url:
            parts.append(
                f'<p style="margin-top: 12px;">'
                f'<img src="{image_url}" alt="投稿画像" style="max-width: 400px; border-radius: 8px;">'
                f'</p>'
            )
        parts.append('</body></html>')
        return ''.join(parts)


class Notifier:
    """複数チャネルをまとめて扱うファサード"""

    def __init__(self, channels: List[NotificationChannel], enabled: bool = True):
        self.channels = channels
        self.enabled = enabled

    def notify_success(
        self,
        platform: str,
        caption: str,
        post_url: Optional[str] = None,
        image_url: Optional[str] = None,
        post_id: Optional[str] = None,
    ) -> None:
        """投稿成功の通知を送る"""
        if not self.enabled or not self.channels:
            return

        title = f'✅ {platform} 投稿成功'
        preview = caption[:100] + ('…' if len(caption) > 100 else '')
        body_lines = [
            f'{platform}への投稿が完了しました。',
            '',
            f'時刻: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        ]
        if post_id:
            body_lines.append(f'投稿ID: {post_id}')
        body_lines.extend(['', '──── キャプション ────', preview])
        body = '\n'.join(body_lines)

        self._broadcast(title, body, link=post_url, image_url=image_url)

    def notify_failure(
        self,
        platform: str,
        caption: str,
        error: str,
    ) -> None:
        """投稿失敗の通知を送る"""
        if not self.enabled or not self.channels:
            return

        title = f'❌ {platform} 投稿失敗'
        preview = caption[:100] + ('…' if len(caption) > 100 else '')
        body = '\n'.join([
            f'{platform}への投稿が失敗しました。',
            '',
            f'時刻: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'エラー: {error}',
            '',
            '──── キャプション ────',
            preview,
        ])

        self._broadcast(title, body)

    def _broadcast(
        self,
        title: str,
        body: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> None:
        for channel in self.channels:
            try:
                channel.send(title=title, body_text=body, link=link, image_url=image_url)
            except Exception as e:
                logger.error(f"通知チャネル {channel.name} でエラー: {e}")


def build_default_notifier() -> Notifier:
    """環境変数から標準的なNotifierを構築"""
    enabled = os.getenv('NOTIFY_ENABLED', 'true').lower() not in ('false', '0', 'no', '')

    channels: List[NotificationChannel] = []

    gmail_user = os.getenv('NOTIFY_GMAIL_USER', '').strip()
    gmail_pass = os.getenv('NOTIFY_GMAIL_APP_PASSWORD', '').strip()
    gmail_to = os.getenv('NOTIFY_GMAIL_TO', '').strip()

    if gmail_user and gmail_pass and gmail_to:
        recipients = [r.strip() for r in gmail_to.split(',') if r.strip()]
        channels.append(GmailChannel(
            sender=gmail_user,
            app_password=gmail_pass,
            recipients=recipients,
        ))
        logger.info(f"GmailChannel 有効: {gmail_user} → {len(recipients)}件")
    else:
        logger.info("GmailChannel 未設定（NOTIFY_GMAIL_* が不足）")

    return Notifier(channels=channels, enabled=enabled)


# ============================================================
# テスト送信用CLI
# ============================================================
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    notifier = build_default_notifier()

    if not notifier.channels:
        print("通知チャネルが1件も設定されていません。.envを確認してください。")
        sys.exit(1)

    # テスト送信
    notifier.notify_success(
        platform='Instagram',
        caption='【テスト通知】\n通知システム動作確認用のメッセージです。\nこれが届いていればGmail SMTP設定は完了しています。',
        post_url='https://www.instagram.com/',
        image_url='https://pub-b525379228434e46a50c4d3f1edae5c7.r2.dev/event-images/starlight_sendai_2026_flyer.png',
        post_id='test_123456',
    )
    print("テスト通知を送信しました。受信トレイをご確認ください。")
