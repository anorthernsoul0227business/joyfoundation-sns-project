#!/usr/bin/env python3
"""記事の書き方の決まりを DB から読む。

2026-09-08: 圭一郎さんの指摘から決まりを育てる流れを作った。
コードに書き足すとAIが承認のたびにコードを書き換えることになるため、
決まりは writing_rules テーブルに置き、生成時にプロンプトへ足す。
承認しても行が1つ増えるだけで、再デプロイは要らない。
"""
from __future__ import annotations

import json
import os
import urllib.request


def active_rules(scope: str) -> list[dict]:
    """有効な決まりを返す。scope は 'weekly' か 'event'。"""
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return []
    q = (f"{url}/rest/v1/writing_rules?select=body,origin&active=is.true"
         f"&scope=in.({scope},both)&order=created_at")
    req = urllib.request.Request(q)
    for h, v in [("apikey", key), ("Authorization", f"Bearer {key}")]:
        req.add_header(h, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode() or "[]")
    except Exception:
        # 決まりが読めなくても記事は作れる。黙って既定の書き方で続ける
        return []


def as_prompt(scope: str) -> str:
    """プロンプトに足す文。決まりが無ければ空文字。"""
    rules = active_rules(scope)
    if not rules:
        return ""
    lines = ["", "## 圭一郎さんのご指摘から決まったこと", ""]
    for r in rules:
        lines.append(f"- {r['body'].strip()}")
    lines.append("")
    return "\n".join(lines)
