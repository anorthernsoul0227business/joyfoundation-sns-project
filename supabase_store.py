#!/usr/bin/env python3
"""週次ループから Supabase の共有ボードへ読み書きする。

PostgREST（Supabase の REST API）を標準ライブラリだけで叩く。psycopg を入れると
launchd 上の実行環境に依存が増えるため、urllib で済ませている。

必要な環境変数（プロジェクト直下の .env に置く）:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

service_role は RLS を通り抜けるため、このモジュールはサーバー側専用。
ブラウザに渡してはいけない。
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

PLATFORM = {"X": "x", "Instagram": "ig", "note": "note", "YouTube": "youtube", "LINE": "line"}
PLATFORM_BACK = {v: k for k, v in PLATFORM.items()}

TEST_BANNER = "【ループ検証テスト・投稿しないでください】"


class SupabaseError(RuntimeError):
    pass


def _config() -> tuple[str, str] | None:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    return (url, key) if url and key else None


def enabled() -> bool:
    """Supabase への書き込みが設定されているか。"""
    return _config() is not None


def _request(method: str, path: str, body=None, prefer: str = "") -> list | dict | None:
    cfg = _config()
    if cfg is None:
        raise SupabaseError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY が設定されていません（.env を確認してください）"
        )
    url, key = cfg
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{url}/rest/v1/{path}", data=data, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    if prefer:
        req.add_header("Prefer", prefer)

    # 通信断で生成物を捨てないよう、シート書き込みと同じ考えで再試行する
    last: Exception | None = None
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                raw = res.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            # 4xx は再試行しても直らない（制約違反・権限など）
            if 400 <= e.code < 500:
                raise SupabaseError(f"HTTP {e.code}: {detail}") from e
            last = SupabaseError(f"HTTP {e.code}: {detail}")
        except Exception as e:  # URLError, socket.timeout など
            last = e
        wait = 3 * (2 ** i)
        logger.warning(f"Supabase への通信に失敗（{i+1}/4）: {type(last).__name__}。{wait}秒後に再試行")
        time.sleep(wait)
    raise SupabaseError(str(last))


def org_id() -> str:
    """書き込み先の組織。いまは1つだけなので最初のものを使う。"""
    rows = _request("GET", "organizations?select=id&order=created_at.asc&limit=1")
    if not rows:
        raise SupabaseError("organizations が空です。先に Web からサインアップしてください")
    return rows[0]["id"]


def title_of(body: str) -> str:
    """一覧に出す見出し。本文の【見出し】、無ければ最初の行。"""
    body = body.replace(TEST_BANNER, "").strip()
    m = re.search(r"【([^】]{2,40})】", body)
    if m:
        return m.group(1)
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:40]
    return ""


def next_article_no() -> str:
    """DB のシーケンスから記事番号を採る（行数から数えない）。"""
    got = _request("POST", "rpc/next_article_no", body={})
    return got if isinstance(got, str) else str(got)


def insert_articles(posts: list, results: list, week: str, test_mode: bool) -> list[dict]:
    """記事を articles に入れ、画像を attachments に入れる。

    戻り値は挿入された記事（article_no と id を含む）。
    """
    oid = org_id()
    rows = []
    for post, res in zip(posts, results):
        body = post.get("本文", "")
        if test_mode:
            body = f"{TEST_BANNER}\n\n{body}"
        grade = (res.get("grade") or "")[:1]
        imgs = post.get("画像", [])
        row = {
            "org_id": oid,
            "week": week,
            "platform": PLATFORM.get(post.get("媒体", ""), "x"),
            "grade": grade if grade in ("A", "B", "C") else None,
            "source_card_ids": post.get("使用カードID", []),
            "title": title_of(body),
            "body_ai": body,
            "status": "needs_check" if res.get("problems") else "ai_draft",
            "image_reason": " ／ ".join(f'{i["id"]}: {i["why"]}' for i in imgs) or None,
        }
        # 検証用は番号でも見分けられるようにする。通常は DB の既定値に任せる
        if test_mode:
            row["article_no"] = "TEST-" + next_article_no()
        rows.append(row)

    inserted = _request("POST", "articles", body=rows, prefer="return=representation")
    if not isinstance(inserted, list) or len(inserted) != len(rows):
        raise SupabaseError(f"挿入された行数が想定と違います: {inserted!r}")

    attachments = []
    for art, post in zip(inserted, posts):
        for order, img in enumerate(post.get("画像", [])):
            attachments.append({
                "org_id": oid,
                "owner_type": "article",
                "owner_id": art["id"],
                "storage_path": f'drive/{img["id"]}',
                "public_url": img["preview"],
                "mime_type": "image/jpeg",
                "sort_order": order,
                "caption": img["id"],
                "drive_file_id": _drive_id(img.get("open", "")),
            })
    if attachments:
        _request("POST", "attachments", body=attachments, prefer="return=minimal")

    return inserted


def _drive_id(url: str) -> str | None:
    m = re.search(r"/d/([A-Za-z0-9_-]{10,})", url)
    return m.group(1) if m else None


def load_recent(limit: int = 24) -> list:
    """直近の記事の「媒体・使用カード・書き出し」。切り口の重複を避けるために使う。"""
    rows = _request(
        "GET",
        "articles?select=platform,source_card_ids,body_ai"
        f"&order=created_at.desc&limit={limit}",
    )
    out = []
    for r in rows or []:
        body = (r.get("body_ai") or "").replace(TEST_BANNER, "").strip()
        out.append({
            "媒体": PLATFORM_BACK.get(r.get("platform", ""), r.get("platform", "")),
            "使用カード": ", ".join(r.get("source_card_ids") or []),
            "書き出し": body.split("\n")[0][:46] if body else "",
        })
    out.reverse()  # 呼び出し側は「古い→新しい」の順を期待している
    return out
