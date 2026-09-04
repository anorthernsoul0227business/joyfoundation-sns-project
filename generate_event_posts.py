#!/usr/bin/env python3
"""イベントの告知記事を作る。

Google カレンダーに予定が入ったら、その時点で告知記事を用意する。
圭一郎さんが確認して OK を出せば、announce_plan の日取りで投稿される。

    /usr/bin/python3 generate_event_posts.py --dry-run
    /usr/bin/python3 generate_event_posts.py --only <series_run_key>
    /usr/bin/python3 generate_event_posts.py

## 作らない場合

  ・すでに作った催し（articles_generated_at が入っている）
  ・告知しないと決めた催し（announce_skip）
  ・開催が明日以前で、もう告知が間に合わない催し

## 圭一郎さんの判断を待つところ

告知開始日（announce_from）は圭一郎さんが決める。未設定でも記事は作るが、
「いつから出すか教えてください」とイベント画面に出す。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import announce_plan

logger = logging.getLogger("generate_event_posts")

JST = dt.timezone(dt.timedelta(hours=9))
PLATFORM_JA = {"x": "X", "ig": "Instagram", "note": "note"}
LIMITS = {"x": "140字以内（ハッシュタグ・改行を含む）",
          "ig": "400〜600字", "note": "1,500〜2,500字"}

PROMPT = """あなたは、音による健康法を広める団体「サウンドヒーリング協会」の
SNS担当者です。下のイベントの告知文を書いてください。

## イベント

{event}

## 書く媒体

{platform}（{limit}）

## 守ること

- **事実は下の情報だけを使ってください。** 日時・場所・費用を、書かれていない
  ことまで補わないでください。分からないことは書かない、が正解です。
- 効果を断言しないでください（「治る」「改善する」は使わない）。
- 数値や研究の話を新しく持ち出さないでください。この記事は告知です。
- 参加を急かす表現（「今すぐ」「残りわずか」）は使わないでください。
- 日付は「9月17日」の形で書いてください。複数日ある場合はすべて挙げてください。
- 最後に申し込み方法への導線を一言入れてください。
  X と Instagram は「詳しくはプロフィールへ。」、note は「お申し込みはリンクから。」
- Instagram と X は最後に #KITAサウンドヒーリング を付けてください。

## 出力

本文だけを出力してください。説明や前置きは書かないでください。
"""


def sb(method: str, path: str, body=None):
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
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


def jst_date(iso: str) -> dt.date:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(JST).date()


def describe_event(events: list[dict]) -> str:
    """LLM に渡すイベントの説明。書かれていないことは書かない。"""
    first = events[0]
    lines = [f"催しの名前: {first['title']}"]
    days = []
    for e in sorted(events, key=lambda x: x["starts_at"]):
        d = jst_date(e["starts_at"])
        s = f"{d.month}月{d.day}日"
        if not e.get("all_day"):
            t = dt.datetime.fromisoformat(e["starts_at"].replace("Z", "+00:00")).astimezone(JST)
            s += f" {t.hour}時" + (f"{t.minute}分" if t.minute else "")
        days.append(s)
    lines.append("開催日: " + "、".join(days))
    if first.get("venue"):
        lines.append(f"会場: {first['venue']}")
    if first.get("price_text"):
        lines.append(f"費用: {first['price_text']}")
    if first.get("description"):
        lines.append(f"補足: {first['description'][:300]}")
    return "\n".join(lines)


# X の140字は投稿できるかどうかの絶対条件。超えたら作り直させる
HARD_LIMIT = {"x": 140}


def write_body(events: list[dict], platform: str, timeout: int) -> str:
    from run_weekly_loop import run_llm
    prompt = PROMPT.format(event=describe_event(events),
                           platform=PLATFORM_JA[platform], limit=LIMITS[platform])
    limit = HARD_LIMIT.get(platform)

    text = ""
    for attempt in range(3):
        out = run_llm(["claude", "-p", prompt, "--output-format", "text"],
                      f"告知文（{platform}）", timeout, timeout + 300)
        raw = out.stdout if hasattr(out, "stdout") else str(out)
        text = raw.strip().strip("`").strip()
        if limit is None:
            return text
        n = len(text)
        if n <= limit:
            return text
        logger.warning(f"   {PLATFORM_JA[platform]}: {n}字で上限{limit}字を超えました。作り直します")
        # 何字削ればよいかを具体的に伝える。曖昧に「短く」と言うと効きにくい
        prompt = (PROMPT.format(event=describe_event(events),
                                platform=PLATFORM_JA[platform], limit=LIMITS[platform])
                  + f"\n\n## 追加の指示\n\n前回は{n}字になり、{n - limit}字超えました。"
                    f"必ず{limit}字以内に収めてください。日時・場所・申し込み導線・"
                    f"ハッシュタグは残し、説明の部分を削ってください。")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="series_run_key を指定して1件だけ")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--today", help="YYYY-MM-DD（検証用）")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    rows = sb("GET", "events?select=*&order=starts_at") or []
    runs: dict[str, list[dict]] = collections.defaultdict(list)
    for e in rows:
        if jst_date(e["starts_at"]) >= today:
            runs[e["series_run_key"] or e["id"]].append(e)

    org_id = rows[0]["org_id"] if rows else None
    made = skipped = 0

    for key, events in sorted(runs.items(), key=lambda kv: kv[1][0]["starts_at"]):
        if args.only and key != args.only:
            continue
        first = events[0]
        first_day = jst_date(first["starts_at"])

        if first.get("announce_skip"):
            logger.info(f"— {first['title'][:26]}: 告知しない設定のためとばします")
            skipped += 1
            continue
        if first.get("articles_generated_at"):
            skipped += 1
            continue

        announce_from = (dt.date.fromisoformat(first["announce_from"])
                         if first.get("announce_from") else None)
        plan = announce_plan.plan_for(first_day, today, announce_from)
        if not plan:
            logger.warning(f"— {first['title'][:26]}（{first_day}）: もう告知が間に合いません")
            skipped += 1
            continue

        need = sorted({p for _, p, _ in plan})
        logger.info(f"■ {first['title'][:30]}（{first_day}、{len(events)}回）")
        logger.info(f"   予定: {announce_plan.describe(first_day, today, announce_from)}")

        bodies: dict[str, str] = {}
        for platform in need:
            try:
                bodies[platform] = write_body(events, platform, args.timeout)
                logger.info(f"   {PLATFORM_JA[platform]}: {len(bodies[platform])}字")
            except Exception as e:
                logger.error(f"   {PLATFORM_JA[platform]} の生成に失敗: {type(e).__name__}: {e}")

        if not bodies:
            skipped += 1
            continue

        if args.dry_run:
            for platform, body in bodies.items():
                print(f"\n--- {PLATFORM_JA[platform]} ---\n{body}\n")
            made += 1
            continue

        # 同じ本文を、予定された回数ぶん記事にする。
        # 圭一郎さんは1本ずつ確認し、それぞれの日に投稿される
        new_articles = []
        for when, platform, role in plan:
            if platform not in bodies:
                continue
            new_articles.append({
                "org_id": org_id,
                "platform": platform,
                "title": first["title"][:40],
                "body_ai": bodies[platform],
                "status": "ai_draft",
                "event_date": first_day.isoformat(),
                "event_series_key": first.get("series_key"),
                "event_run_key": key,
                "announce_role": role,
                "scheduled_date": when.isoformat(),
                "grade": "A",   # 告知は既存の事実のみ。新しい数値を含まない
            })
        got = sb("POST", "articles", body=new_articles)
        logger.info(f"   → {len(got or [])}本の告知記事を作りました")

        for e in events:
            sb("PATCH", f"events?id=eq.{e['id']}",
               {"articles_generated_at": dt.datetime.now(JST).isoformat()})
        made += 1

    logger.info(f"完了: 作成 {made}件 / とばした {skipped}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
