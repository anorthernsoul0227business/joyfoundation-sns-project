#!/usr/bin/env python3
"""投稿できたことを共有ボード（Supabase）に伝える。

2026-09-06: 投稿は成功したのに、ボード側は「投稿予約」のままだった。
投稿処理がスプレッドシートのステータスしか更新しておらず、
圭一郎さんの画面では出たのか出ていないのか分からない状態だった。

投稿キューの「メモ」欄に `共有ボード ART-0049` と入れてあるので、
そこから記事を特定して published にする。

投稿そのものは成功しているので、ここで失敗しても投稿処理は止めない。
記録が遅れるだけで、実害はない。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

JST = dt.timezone(dt.timedelta(hours=9))
MEMO_PAT = re.compile(r"共有ボード\s+((?:TEST-)?ART-[0-9]+(?:-[0-9]+)?)")


def article_no_from_memo(memo: str) -> str | None:
    """投稿キューのメモ欄から記事番号を取り出す。"""
    m = MEMO_PAT.search(memo or "")
    return m.group(1) if m else None


def mark_published(article_no: str, post_id: str = "", logger=None) -> bool:
    """記事を「投稿済」にする。できなければ False を返すだけで例外は投げない。"""
    def say(msg):
        if logger:
            logger.warning(msg)

    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        say("共有ボードへの記録をとばします（SUPABASE_URL / SERVICE_ROLE_KEY が未設定）")
        return False

    body = {"status": "published", "published_at": dt.datetime.now(JST).isoformat()}
    req = urllib.request.Request(
        f"{url}/rest/v1/articles?article_no=eq.{urllib.parse.quote(article_no)}",
        data=json.dumps(body).encode(), method="PATCH")
    for h, v in [("apikey", key), ("Authorization", f"Bearer {key}"),
                 ("Content-Type", "application/json"), ("Prefer", "return=representation")]:
        req.add_header(h, v)

    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                got = json.loads(r.read().decode() or "[]")
            if got:
                if logger:
                    logger.info(f"  共有ボードを『投稿済』にしました: {article_no}")
                return True
            say(f"共有ボードに {article_no} が見つかりませんでした")
            return False
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(2 * (2 ** attempt))
    say(f"共有ボードへの記録に失敗しました（{type(last).__name__}）。投稿自体は成功しています")
    return False
