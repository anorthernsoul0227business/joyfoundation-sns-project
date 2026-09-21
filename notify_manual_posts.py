#!/usr/bin/env python3
"""手で投稿する必要がある記事（note）を、当日の朝に知らせる。

2026-09-19〜21 に起きたこと: note には自動投稿の仕組みがないため手作業が要るが、
それを知らせる仕組みがなかった。ART-0078 は 9/9 に投稿する予定のまま10日過ぎ、
9/19 の開催日を迎えて出せなくなった。

投稿予定日の朝に、本文をそのまま貼れる形でメールする。
「あとでやろう」と思っても思い出せる材料を手元に届ける。

    /usr/bin/python3 notify_manual_posts.py --dry-run
    /usr/bin/python3 notify_manual_posts.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from patrol import sb

logger = logging.getLogger("notify_manual_posts")
JST = dt.timezone(dt.timedelta(hours=9))
BOARD_URL = "https://shc-sns-calendar-web.vercel.app/board"

# 自動投稿できない媒体。X と Instagram は投稿ジョブが拾う
MANUAL_PLATFORMS = {"note", "youtube", "line"}
PLATFORM_JA = {"note": "note", "youtube": "YouTube", "line": "LINE"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", help="YYYY-MM-DD（検証用）")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    plats = ",".join(MANUAL_PLATFORMS)

    # 今日ぶんに加え、取りこぼした過去ぶんも拾う。
    # 予定日を過ぎても、開催日前なら出す意味がある
    rows = sb("GET", f"articles?select=article_no,platform,title,body_ai,body_final,"
                     f"scheduled_date,event_date&status=eq.scheduled"
                     f"&platform=in.({plats})&scheduled_date=lte.{today.isoformat()}"
                     "&order=scheduled_date") or []
    if not rows:
        logger.info("手で投稿する記事はありません。")
        return 0

    parts = ["康二郎さま", "",
             "手で投稿していただく記事があります。",
             "note には自動で投稿する仕組みがないため、お手数ですがお願いします。", ""]
    for a in rows:
        body = a["body_final"] or a["body_ai"]
        when = a.get("scheduled_date") or ""
        late = ""
        if when and when < today.isoformat():
            late = f"（{(today - dt.date.fromisoformat(when)).days}日 予定を過ぎています）"
        ev = ""
        if a.get("event_date"):
            evd = dt.date.fromisoformat(a["event_date"])
            left = (evd - today).days
            ev = f"　※ {evd} のイベント告知です。" + (
                "開催日を過ぎているので、もう出せません。" if left < 0
                else f"あと{left}日です。" if left <= 2 else "")
        parts += [
            "=" * 46,
            f"{PLATFORM_JA.get(a['platform'], a['platform'])}　{a['article_no']}　予定 {when}{late}",
            f"{a['title']}{ev}",
            "=" * 46, "", body, "",
        ]
        logger.info(f"  {a['article_no']} {a['platform']} 予定={when}{late}")

    parts += [
        "投稿が終わりましたら、共有ボードで記事を開き、",
        "「このまま出す」ではなく、投稿済みとしてお片づけください。",
        BOARD_URL, "",
    ]
    body_text = "\n".join(parts)

    if args.dry_run:
        print(body_text[:1400])
        return 0

    try:
        from notifier import GmailChannel
        ch = GmailChannel(
            sender=os.getenv("NOTIFY_GMAIL_USER", ""),
            app_password=os.getenv("NOTIFY_GMAIL_APP_PASSWORD", ""),
            recipients=[os.getenv("LOOP_NOTIFY_TO") or os.getenv("NOTIFY_GMAIL_USER", "")],
            display_name="ジョイファンデーション 共有ボード",
        )
        ch.send(f"【手で投稿】note の記事が{len(rows)}件あります", body_text)
        logger.info(f"お知らせしました（{len(rows)}件）")
    except Exception as e:
        logger.error(f"送れませんでした: {type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
