#!/usr/bin/env python3
"""圭一郎さんの Google カレンダーを共有ボードの events に取り込む。

2026-09-02 まで、イベントの開催日はスプレッドシートの「イベント予定」タブに
手で入力していた。圭一郎さんのカレンダー（keiichiro.kita@gmail.com）が
サービスアカウントに共有されたので、以後はそちらを正本にする。

    /usr/bin/python3 sync_events.py --dry-run
    /usr/bin/python3 sync_events.py

## 費用などの補足

カレンダーには費用欄が無い。「一般3,000円／会員2,000円」のような情報は
スプレッドシート側にしかないため、タイトルが一致する行から拾って補う。

## confirmed_by_owner について

カレンダーは圭一郎さんご本人のものだが、下書きの予定や社内向けの予定も
混じりうる。告知記事の根拠にしてよいかは別途ご本人に確認していただく方針なので、
取り込み時点では false のままにする。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("sync_events")

CALENDAR_ID = "keiichiro.kita@gmail.com"
SA_FILE = os.path.expanduser("~/.config/gspread/service_account.json")
SPREADSHEET_KEY = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
MONTHS_AHEAD = 6


def calendar_events(since: dt.date) -> list[dict]:
    from google.oauth2 import service_account
    import google.auth.transport.requests as gtr

    creds = service_account.Credentials.from_service_account_file(
        SA_FILE, scopes=["https://www.googleapis.com/auth/calendar.readonly"])
    creds.refresh(gtr.Request())

    cid = urllib.parse.quote(CALENDAR_ID)
    until = since + dt.timedelta(days=31 * MONTHS_AHEAD)
    out, token = [], None
    while True:
        q = {
            "timeMin": f"{since.isoformat()}T00:00:00Z",
            "timeMax": f"{until.isoformat()}T00:00:00Z",
            "singleEvents": "true",     # 繰り返し予定を1回ずつに展開する
            "orderBy": "startTime",
            "maxResults": "250",
        }
        if token:
            q["pageToken"] = token
        req = urllib.request.Request(
            f"https://www.googleapis.com/calendar/v3/calendars/{cid}/events?"
            + urllib.parse.urlencode(q))
        req.add_header("Authorization", f"Bearer {creds.token}")
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.loads(r.read().decode())
        out += page.get("items", [])
        token = page.get("nextPageToken")
        if not token:
            return out


def normalize(t: str) -> str:
    """照合用にタイトルを均す。

    カレンダーとシートで表記が揺れている（「ウエルビーイング」と「ウェルビーイング」、
    空白の有無、「食X音」と「食ｘ音」など）。先頭一致では拾えなかったため、
    揺れを潰したうえで類似度で照合する。
    """
    import re
    import unicodedata
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[\s　・,、。()（）]", "", t)
    for a, b in [("ェ", "エ"), ("ォ", "オ"), ("ァ", "ア"), ("ィ", "イ"), ("ゥ", "ウ")]:
        t = t.replace(a, b)
    return t.lower()


def sheet_extras() -> dict[str, list[dict]]:
    """シートから費用・備考を拾う。開催日ごとにまとめる。"""
    import gspread
    rows = gspread.service_account().open_by_key(SPREADSHEET_KEY).worksheet("イベント予定").get_all_values()
    hdr = rows[0]
    idx = {name: hdr.index(name) for name in hdr}
    out: dict[str, list[dict]] = {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        def col(name):
            i = idx.get(name)
            return r[i].strip() if i is not None and len(r) > i else ""
        out.setdefault(r[0].strip(), []).append({
            "title": col("イベント名"),
            "price_text": col("費用") or None,
            "description": col("詳細メモ") or None,
            "venue_sheet": col("開催場所") or None,
        })
    return out


def match_extra(day: str, title: str, extras: dict[str, list[dict]]) -> dict:
    """同じ日のシート行から、タイトルが一番近いものを返す。"""
    from difflib import SequenceMatcher
    cands = extras.get(day, [])
    if not cands:
        return {}
    if len(cands) == 1:
        return cands[0]
    want = normalize(title)
    best = max(cands, key=lambda c: SequenceMatcher(None, want, normalize(c["title"])).ratio())
    score = SequenceMatcher(None, want, normalize(best["title"])).ratio()
    return best if score >= 0.5 else {}


def sb(method: str, path: str, body=None):
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
        method=method)
    for h, v in [("apikey", key), ("Authorization", f"Bearer {key}"),
                 ("Content-Type", "application/json"),
                 ("Prefer", "return=representation,resolution=merge-duplicates")]:
        req.add_header(h, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:400]}") from e


def to_row(ev: dict, org_id: str, extras: dict) -> dict | None:
    start, end = ev.get("start", {}), ev.get("end", {})
    all_day = "date" in start
    if all_day:
        d = start.get("date")
        if not d:
            return None
        starts_at = f"{d}T00:00:00+09:00"
        # 終日予定の end は翌日を指すので、そのまま入れると1日ずれる
        ends_at = None
    else:
        starts_at = start.get("dateTime")
        ends_at = end.get("dateTime")
        if not starts_at:
            return None

    day = starts_at[:10]
    title = (ev.get("summary") or "(無題)").strip()
    ex = match_extra(day, title, extras)

    venue = ev.get("location")
    if venue:
        venue = venue.split(",")[0].strip()   # 「, 日本、〒152-…」を落とす
    return {
        "org_id": org_id,
        "google_event_id": ev["id"],
        "title": title,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "all_day": all_day,
        "venue": venue or ex.get("venue_sheet"),
        "price_text": ex.get("price_text"),
        "description": ex.get("description") or (ev.get("description") or None),
        "url": ev.get("htmlLink"),
        "source": "l4_calendar",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    orgs = sb("GET", "organizations?select=id&order=created_at.asc&limit=1")
    if not orgs:
        logger.error("organizations が空です")
        return 1
    org_id = orgs[0]["id"]

    since = dt.date.today() - dt.timedelta(days=7)
    events = calendar_events(since)
    logger.info(f"カレンダーから {len(events)}件（{since} 以降）")

    try:
        extras = sheet_extras()
        logger.info(f"シートから補足 {len(extras)}件")
    except Exception as e:
        logger.warning(f"シートの補足を読めませんでした: {type(e).__name__}: {e}")
        extras = {}

    rows = [r for r in (to_row(e, org_id, extras) for e in events) if r]
    with_price = sum(1 for r in rows if r["price_text"])
    logger.info(f"取り込む {len(rows)}件（うち費用あり {with_price}件）")

    for r in rows[:40]:
        logger.info(f"  {r['starts_at'][:16].replace('T',' ')} {r['title'][:34]:36}"
                    f" {r['venue'] or '':18} {r['price_text'] or ''}")

    if args.dry_run:
        logger.info("--dry-run のため書き込みませんでした")
        return 0

    # google_event_id の一意制約で、二度流しても増えず、変更は上書きされる
    sb("POST", "events?on_conflict=org_id,google_event_id", body=rows)
    total = sb("GET", "events?select=id&limit=1000") or []
    logger.info(f"完了。events は {len(total)}件になりました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
