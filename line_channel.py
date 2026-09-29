#!/usr/bin/env python3
"""LINE で康二郎さんにお知らせする。

2026-09-30 康二郎さんの要望。メールだと埋もれるため、次の3つだけ LINE にも送る。
  ・手で投稿する note の記事（予定日の朝）
  ・圭一郎さんのメモに返事がまだ
  ・月曜に圭一郎さんへ送ったお知らせの控え

## 安全のために

公式アカウント @868hqnfw は会員向けにも使われている。
誤って全員に送る事故を防ぐため、**broadcast は使わない**。
宛先（LINE_NOTIFY_TO）が設定されていなければ、何もせずに終わる。

## LINE Notify は使えない

かつて個人向け通知に広く使われていたが、2026-03-31 にサービス終了。
古い記事にはよく出てくるが、いまは Messaging API を使う。
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

PUSH_URL = "https://api.line.me/v2/bot/message/push"
# LINE の1通あたりの上限は5000字。余裕を持って切る
MAX_TEXT = 4800


class LineChannel:
    """Messaging API の push でお知らせする。

    notifier.NotificationChannel と同じ形にしてあるので、
    既存の通知処理にそのまま差し込める。
    """

    def __init__(self, token: str, to: str):
        self.token = token
        self.to = to

    @property
    def name(self) -> str:
        return "line"

    def send(self, title: str, body_text: str, body_html=None,
             link=None, image_url=None) -> bool:
        if not self.token or not self.to:
            logger.warning("LINE の設定がないため送りません（LINE_CHANNEL_TOKEN / LINE_NOTIFY_TO）")
            return False

        text = f"{title}\n\n{body_text}".strip()
        if link:
            text += f"\n\n{link}"
        if len(text) > MAX_TEXT:
            text = text[:MAX_TEXT - 20] + "\n…（続きはメールで）"

        body = json.dumps({
            "to": self.to,                      # 宛先を必ず指定する。broadcast は使わない
            "messages": [{"type": "text", "text": text}],
        }, ensure_ascii=False).encode()

        req = urllib.request.Request(PUSH_URL, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")

        last = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    if r.status == 200:
                        logger.info(f"LINE でお知らせしました: {title[:30]}")
                        return True
                    last = f"HTTP {r.status}"
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:200]
                # 4xx は再試行しても直らない（トークン切れ、宛先違いなど）
                if 400 <= e.code < 500:
                    logger.error(f"LINE に送れませんでした（HTTP {e.code}）: {detail}")
                    return False
                last = f"HTTP {e.code}"
            except Exception as e:
                last = f"{type(e).__name__}"
            if attempt < 2:
                time.sleep(3 * (2 ** attempt))
        logger.error(f"LINE に送れませんでした（{last}）")
        return False


def build_line_channel() -> LineChannel | None:
    """設定があれば LINE のお知らせ口を作る。無ければ None。"""
    token = os.getenv("LINE_CHANNEL_TOKEN", "").strip()
    to = os.getenv("LINE_NOTIFY_TO", "").strip()
    if not token or not to:
        return None
    return LineChannel(token, to)


def notify_line(title: str, body: str, link: str | None = None) -> bool:
    """設定があれば LINE にも送る。無ければ黙って何もしない。

    メールは今までどおり送られるので、LINE が使えなくても情報は届く。
    """
    ch = build_line_channel()
    if ch is None:
        return False
    try:
        return ch.send(title, body, link=link)
    except Exception as e:
        logger.warning(f"LINE のお知らせをとばしました: {type(e).__name__}: {e}")
        return False
