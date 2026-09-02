#!/usr/bin/env python3
"""承認された記事の投稿日時を決め、投稿キューへ渡す。

2026-09-02 まで、承認と投稿キューの間は人が繋いでいた。そこが途絶えて
6/16 から一本も投稿されていなかった。ここを自動化する。

    /usr/bin/python3 schedule_posts.py --dry-run   # 決めた予定を表示するだけ
    /usr/bin/python3 schedule_posts.py             # キューに入れる

## 日取りの決め方

イベント記事（本文に開催日が書いてある）:
    開催の LEAD_DAYS 日前に置く。そこが過ぎていれば前日まで詰める。
    前日も過ぎていれば投稿せず missed にする。黙って期日後に出さない。

それ以外:
    翌日から順に、空いている日へ 1日1件ずつ。

いずれも「同じ媒体で1日1件」「同じイベントの記事を同じ日に重ねない」を守る。

## note について

note には自動投稿の仕組みが無い（X と Instagram のみ）。
note の記事は日時だけ決めて scheduled にし、キューには入れない。
手で投稿する必要がある。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("schedule_posts")

SPREADSHEET_KEY = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
QUEUE_TAB = {"x": "X投稿キュー", "ig": "IG投稿キュー"}
AUTO_PLATFORMS = set(QUEUE_TAB)          # 自動投稿できる媒体
POST_HOUR, POST_MINUTE = 12, 0
# Supabase は TIMESTAMPTZ を UTC で返す。日本時間に直してから日付を取らないと、
# 終日予定（日本時間 0:00 保存）が前日 15:00 UTC となり1日ずれる
JST = dt.timezone(dt.timedelta(hours=9))
LEAD_DAYS = 3                            # イベントの何日前に出すか
MIN_LEAD_DAYS = 1                        # 最低でも前日には出す


def sb(method: str, path: str, body=None):
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY がありません")
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
        method=method)
    for h, v in [("apikey", key), ("Authorization", f"Bearer {key}"),
                 ("Content-Type", "application/json"), ("Prefer", "return=representation")]:
        req.add_header(h, v)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else None


DATE_PAT = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})|(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def load_events() -> dict[dt.date, dict]:
    """開催日ごとのイベント。本文の日付がイベントかの判定と、告知の何日前かに使う。

    2026-09-02: 正本をスプレッドシートから圭一郎さんの Google カレンダーへ移した。
    カレンダーは sync_events.py が events テーブルに取り込む。
    予定が増えてもこちらの手入力は不要になる。
    """
    rows = sb("GET", "events?select=starts_at,title,lead_days&order=starts_at") or []
    out: dict[dt.date, dict] = {}
    for e in rows:
        d = dt.datetime.fromisoformat(e["starts_at"].replace("Z", "+00:00")).astimezone(JST).date()
        # 同じ日に複数あるときは、告知を早く出したい方（lead_days が大きい方）に合わせる
        cur = out.get(d)
        if cur is None or (e.get("lead_days") or 0) > (cur.get("lead_days") or 0):
            out[d] = e
    return out


def find_event_date(body: str, today: dt.date, known: set[dt.date]) -> dt.date | None:
    """本文が触れているイベント開催日を返す。

    「9/8」「9月8日」の両方を拾う。ただし本文には研究の実施日（「8月20日の記録では」）
    のような日付も出てくる。それを告知と誤解して見送りにしないよう、
    イベント予定シートに載っている日付だけをイベントとみなす。
    """
    found = []
    for m in DATE_PAT.finditer(body):
        mo, d = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        for year in (today.year, today.year + 1):
            try:
                cand = dt.date(year, int(mo), int(d))
            except ValueError:
                continue
            if cand >= today - dt.timedelta(days=31) and cand in known:
                found.append(cand)
                break
    return min(found) if found else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", help="YYYY-MM-DD（検証用に今日を差し替える）")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    approved = sb("GET", "articles?select=*&status=eq.approved&order=reviewed_at") or []
    if not approved:
        logger.info("投稿日を決める記事はありません。")
        return 0

    events = load_events()
    known = set(events)
    logger.info(f"カレンダー由来のイベント {len(known)}日分を読みました")

    # すでに予約済みの枠を埋めておく。二重に同じ日へ入れないため
    taken: set[tuple[str, dt.date]] = set()
    event_used: set[tuple[str, dt.date]] = set()
    for a in sb("GET", "articles?select=platform,scheduled_at,event_date&status=in.(scheduled,published)") or []:
        if a.get("scheduled_at"):
            d = dt.datetime.fromisoformat(a["scheduled_at"].replace("Z", "+00:00")).astimezone(JST).date()
            taken.add((a["platform"], d))
            if a.get("event_date"):
                event_used.add((a["event_date"], d))

    logger.info(f"{len(approved)}件の投稿日を決めます（今日 {today}）")
    plan, missed = [], []

    for a in approved:
        body = a["body_final"] or a["body_ai"]
        ev = find_event_date(body, today, known)
        plat = a["platform"]

        if ev:
            # 開催日から逆算し、埋まっていたら1日ずつ前に詰める。
            # イベントごとに lead_days が設定されていればそれを使う
            lead_start = events.get(ev, {}).get("lead_days") or LEAD_DAYS
            slot = None
            for lead in range(lead_start, MIN_LEAD_DAYS - 1, -1):
                cand = ev - dt.timedelta(days=lead)
                if cand <= today:
                    continue
                if (plat, cand) in taken or (ev.isoformat(), cand) in event_used:
                    continue
                slot = cand
                break
            if slot is None:
                missed.append((a, ev))
                continue
            event_used.add((ev.isoformat(), slot))
        else:
            # 期日のない記事は翌日から順に空きを探す
            slot = today + dt.timedelta(days=1)
            while (plat, slot) in taken:
                slot += dt.timedelta(days=1)

        taken.add((plat, slot))
        when = dt.datetime.combine(slot, dt.time(POST_HOUR, POST_MINUTE), tzinfo=JST)
        plan.append((a, when, ev))

    for a, when, ev in sorted(plan, key=lambda x: x[1]):
        auto = "自動" if a["platform"] in AUTO_PLATFORMS else "手で投稿"
        tag = f"（{ev} のイベント）" if ev else ""
        logger.info(f"  {a['article_no']:12} {a['platform']:5} {when:%Y-%m-%d %H:%M} [{auto}]{tag}")
    for a, ev in missed:
        logger.warning(f"  {a['article_no']:12} {a['platform']:5} 見送り: {ev} のイベントに間に合いません")

    if args.dry_run:
        logger.info("--dry-run のため書き込みませんでした")
        return 0

    import gspread
    gc = gspread.service_account()
    sh = gc.open_by_key(SPREADSHEET_KEY)

    queued = 0
    for a, when, ev in sorted(plan, key=lambda x: x[1]):
        body = a["body_final"] or a["body_ai"]
        patch = {"status": "scheduled", "scheduled_at": when.isoformat(),
                 "scheduled_date": when.date().isoformat(),
                 "event_date": ev.isoformat() if ev else None}

        if a["platform"] in AUTO_PLATFORMS:
            imgs = sb("GET", f"attachments?select=public_url&owner_id=eq.{a['id']}"
                             "&owner_type=eq.article&order=sort_order") or []
            urls = [i["public_url"] for i in imgs][:3]
            # 列: A投稿日時 B本文 C画像1 D画像リンク1 E画像2 F画像リンク2 G画像3 H画像リンク3 Iステータス Jメモ
            row = [when.strftime("%Y-%m-%d %H:%M"), body]
            for i in range(3):
                row += ["", urls[i] if i < len(urls) else ""]
            row += ["投稿予約", f"共有ボード {a['article_no']}"]
            ws = sh.worksheet(QUEUE_TAB[a["platform"]])
            ws.append_row(row, value_input_option="RAW")
            queued += 1

        sb("PATCH", f"articles?article_no=eq.{a['article_no']}", patch)

    for a, ev in missed:
        sb("PATCH", f"articles?article_no=eq.{a['article_no']}",
           {"status": "missed", "event_date": ev.isoformat()})

    manual = len(plan) - queued
    logger.info(f"完了: キューに {queued}件 / 手で投稿する note など {manual}件 / 見送り {len(missed)}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
