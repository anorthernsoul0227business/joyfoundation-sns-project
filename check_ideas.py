#!/usr/bin/env python3
"""思いつきメモに返事がないものを知らせる。

2026-09-08 に判明: メモは書き込まれるだけで、誰も見に行っていなかった。
毎朝の処理は「カレンダー取り込み → 告知記事の生成 → 投稿日の決定」だけで、
メモを見る工程がなかった。9/4 のメモ2件が4日間放置されていた。

圭一郎さんが書いても誰も気づかないのでは、書く意味がなくなる。
返事のないメモがあれば、康二郎さんにメールで知らせる。

    /usr/bin/python3 check_ideas.py            # 未返信があれば通知
    /usr/bin/python3 check_ideas.py --dry-run  # 表示するだけ
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("check_ideas")
# 同じ知らせをくり返さないための控え（notify_owner.py と同じやり方）
STAMP = ROOT / "logs" / "check_ideas_last.json"
JST = dt.timezone(dt.timedelta(hours=9))


def sb(path: str):
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    req = urllib.request.Request(f"{url}/rest/v1/{path}")
    for h, v in [("apikey", key), ("Authorization", f"Bearer {key}")]:
        req.add_header(h, v)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode() or "[]")


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

    # 返事を書いていないメモ。status ではなく reply の有無で見る。
    # status を変えただけで返事を書き忘れる、を防ぐため
    ideas = sb("ideas?select=id,body,status,created_at&reply=is.null&order=created_at.asc")
    if not ideas:
        logger.info("返事待ちのメモはありません。")
        return 0

    now = dt.datetime.now(JST)
    lines = []
    for i in ideas:
        created = dt.datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")).astimezone(JST)
        days = (now - created).days
        mark = "！" if days >= 1 else ""
        lines.append(f"{mark}{created:%m/%d %H:%M}（{days}日前）\n{i['body']}\n")
        logger.info(f"  {created:%m/%d} {days}日前: {i['body'][:44]}")

    logger.warning(f"返事待ちのメモが {len(ideas)}件あります")
    if args.dry_run:
        return 0

    # 同じ知らせを毎日くり返さない。
    # 2026-09-30 圭一郎さんから「同じメールが何度も来る」とのご報告。
    # 返事が付くまで毎朝送り続けていた（送った記録を持っていなかった）
    digest = hashlib.sha256("\n".join(sorted(i["id"] for i in ideas)).encode()).hexdigest()[:16]
    today = now.date().isoformat()
    if STAMP.exists():
        try:
            last = json.loads(STAMP.read_text())
            if last.get("digest") == digest and last.get("date") == today:
                logger.info("同じ内容を今日すでに知らせています。送りません。")
                return 0
        except Exception:
            pass

    try:
        # メールは送らない。
        # 2026-09-30: 宛先が NOTIFY_GMAIL_TO（＝圭一郎さん）になっており、
        # 「あなたのメモにまだ返事がありません」とご本人に毎日届いていた。
        # これは返事をする側（康二郎さん）への連絡なので LINE だけにする
        import line_channel
        line_channel.notify_line(
            f"💡 圭一郎さんのメモ {len(ideas)}件に返事がまだです",
            "\n".join(f"・{i['body'].splitlines()[0][:34]}" for i in ideas),
            "https://shc-sns-calendar-web.vercel.app/board")
        logger.info("LINE でお知らせしました")
        STAMP.parent.mkdir(exist_ok=True)
        STAMP.write_text(json.dumps({"digest": digest, "date": today}, ensure_ascii=False))
    except Exception as e:
        logger.error(f"通知に失敗しました: {type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
