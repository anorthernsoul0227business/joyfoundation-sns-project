#!/usr/bin/env python3
"""圭一郎さんに「確認をお願いします」とメールでお知らせする。

2026-09-19 に判明: 圭一郎さんの最後の操作は9/8で、11日間止まっていた。
新しく確認するものが出ても、圭一郎さんには何も通知されない設計だった。
ご自分で画面を開きに行かない限り気づけない。

9/8 18:00 に AI が書き直した3件は、圭一郎さんが最後に触られた直後に出てきており、
入れ違いになっていた可能性が高い。

    /usr/bin/python3 notify_owner.py --dry-run   # 文面を表示するだけ
    /usr/bin/python3 notify_owner.py             # 送る
    /usr/bin/python3 notify_owner.py --force     # 0件でも送る（検証用）

## 送りすぎないための約束

  ・確認するものが1件も無ければ送らない
  ・同じ内容で1日に2回は送らない（前回の送信内容を控えておく）
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from patrol import sb

logger = logging.getLogger("notify_owner")
JST = dt.timezone(dt.timedelta(hours=9))
BOARD_URL = "https://shc-sns-calendar-web.vercel.app/board"
STAMP = ROOT / "logs" / "notify_owner_last.json"

# 圭一郎さんに見ていただきたい状態
WAITING = {
    "revised": "直しました（ご確認ください）",
    "ai_draft": "まだ見ていただいていません",
    "needs_check": "まだ見ていただいていません",
    "staff_ok": "まだ見ていただいていません",
    "needs_owner_input": "教えていただきたいことがあります",
}


def owner_email() -> str:
    return os.getenv("OWNER_NOTIFY_TO", "").strip() or os.getenv("NOTIFY_GMAIL_TO", "").strip()


def build_body(rows: list[dict]) -> tuple[str, str]:
    by: dict[str, list[dict]] = {}
    for a in rows:
        by.setdefault(a["status"], []).append(a)

    # 急ぎのものを先に伝える。件数だけ並べても動きにくい
    lines = ["喜田圭一郎さま", "", "いつもありがとうございます。",
             "共有ボードで、ご確認をお願いしたい記事がございます。", ""]

    revised = by.get("revised", [])
    asking = by.get("needs_owner_input", [])
    fresh = [a for s in ("ai_draft", "needs_check", "staff_ok") for a in by.get(s, [])]
    # 「もうすぐ」は今日から1週間以内に限る。86件並べても選べない。
    # 同じ催しの記事が何本も続くので、題名が重複するものは1本だけ挙げる
    today = dt.date.today().isoformat()
    limit = (dt.date.today() + dt.timedelta(days=7)).isoformat()
    # 予定日が過ぎているものは急ぎではない（もう出せない）。挙げると混乱する
    soon = [a for a in fresh
            if today <= (a.get("scheduled_date") or "9999") <= limit]
    seen_titles: set[str] = set()
    soon_shown = []
    for a in sorted(soon, key=lambda x: x.get("scheduled_date") or ""):
        t = (a["title"] or "")[:20]
        if t in seen_titles:
            continue
        seen_titles.add(t)
        soon_shown.append(a)

    if revised:
        lines.append(f"■ ご指示にそって直しました（{len(revised)}件）")
        lines.append("  直した箇所を色分けしてお見せします。")
        lines.append("  よろしければ「このまま出す」を押してください。")
        for a in revised[:6]:
            lines.append(f"   ・{a['title'][:34]}")
        lines.append("")

    if asking:
        lines.append(f"■ 教えていただきたいことがあります（{len(asking)}件）")
        lines.append("  ご指示だけでは直し方が決まらなかったものです。")
        for a in asking[:4]:
            lines.append(f"   ・{a['title'][:34]}")
        lines.append("")

    # 未確認の総数（129件など）をそのまま出すと、受け取る側に圧迫感を与える。
    # 投稿日が近いものだけを挙げ、残りは件数も書かない（2026-09-19）
    if soon_shown:
        lines.append(f"■ 1週間以内に投稿する予定の記事（{len(soon)}件）")
        lines.append("  先にこちらをご覧いただけると助かります。")
        for a in soon_shown[:5]:
            when = a.get("scheduled_date") or ""
            head = f"{when[5:7]}/{when[8:10]} " if len(when) == 10 else ""
            lines.append(f"   ・{head}{a['title'][:30]}")
        lines.append("")
    elif fresh:
        lines.append("■ そのほか、お手すきのときにご覧いただける記事もございます。")
        lines.append("")

    lines += [
        "下のページからご覧いただけます。",
        BOARD_URL,
        "",
        "  メールアドレス： kita@h-garden.com",
        "",
        "パソコンでもiPhoneでも開けます。",
        "読みにくいときは、画面の上の「大」を押してください。",
        "",
        "どうぞよろしくお願いいたします。",
        "",
        "喜田康二郎",
    ]
    subject = f"【共有ボード】ご確認をお願いします（{len(revised) + len(asking)}件）" \
        if (revised or asking) else "【共有ボード】ご確認のお願い"
    return subject, "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="同じ内容でも送る")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    statuses = ",".join(WAITING)
    rows = sb("GET", f"articles?select=article_no,title,status,scheduled_date"
                     f"&status=in.({statuses})&order=created_at") or []
    if not rows and not args.force:
        logger.info("ご確認いただくものはありません。送りません。")
        return 0

    subject, body = build_body(rows)
    logger.info(f"確認まち {len(rows)}件")

    if args.dry_run:
        print("=" * 56)
        print("件名:", subject)
        print("宛先:", owner_email() or "(未設定)")
        print("=" * 56)
        print(body)
        return 0

    # 同じ内容で何度も送らない。圭一郎さんの受信箱を埋めないため
    digest = hashlib.sha256(body.encode()).hexdigest()[:16]
    today = dt.datetime.now(JST).date().isoformat()
    if STAMP.exists() and not args.force:
        try:
            last = json.loads(STAMP.read_text())
            if last.get("digest") == digest and last.get("date") == today:
                logger.info("同じ内容を今日すでに送っています。送りません。")
                return 0
        except Exception:
            pass

    to = owner_email()
    if not to:
        logger.error("宛先がありません（OWNER_NOTIFY_TO / NOTIFY_GMAIL_TO）")
        return 1

    try:
        from notifier import GmailChannel
        ch = GmailChannel(
            sender=os.getenv("NOTIFY_GMAIL_USER", ""),
            app_password=os.getenv("NOTIFY_GMAIL_APP_PASSWORD", ""),
            recipients=[to],
            display_name="ジョイファンデーション 共有ボード",
        )
        ch.send(subject, body)
        STAMP.parent.mkdir(exist_ok=True)
        STAMP.write_text(json.dumps({"digest": digest, "date": today}, ensure_ascii=False))
        logger.info(f"お知らせしました → {to}")
    except Exception as e:
        logger.error(f"送れませんでした: {type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
