#!/usr/bin/env python3
"""承認されたやることを実行する。

2026-09-08 康二郎さんの構想。タスクを押すと案が開き、承認すればそのまま実行、
却下なら人が解決するか、思いつきメモに書いてもらって作り直す、という流れの
「そのまま実行」の部分。

    /usr/bin/python3 apply_tasks.py --dry-run
    /usr/bin/python3 apply_tasks.py

## 安全のために

実行できるのは、あらかじめ決めた4種類だけ。
コードの書き換えや再デプロイは行わない。
書き方の決まりは writing_rules に行が1つ増えるだけで、
次の生成から自動的にプロンプトへ足される。

記事を書き直す場合も、圭一郎さんの確認を飛ばさない。
直したものは「直しました（確認まち）」になり、あらためて見ていただく。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from patrol import sb   # 同じ通信処理を使う

logger = logging.getLogger("apply_tasks")
JST = dt.timezone(dt.timedelta(hours=9))


def now() -> str:
    return dt.datetime.now(JST).isoformat()


def reply_to_idea(idea_id: str, text: str) -> None:
    if not text:
        return
    sb("PATCH", f"ideas?id=eq.{idea_id}",
       {"reply": text, "replied_at": now(), "status": "reflected"})


def do_writing_rule(task: dict) -> str:
    """書き方の決まりを足す。コードは触らない。"""
    payload = task.get("proposal_payload") or {}
    body = (payload.get("rule_body") or "").strip()
    if not body:
        raise RuntimeError("決まりの本文が空です")
    sb("POST", "writing_rules", body=[{
        "org_id": task["org_id"],
        "scope": payload.get("scope") or "both",
        "body": body,
        "origin": (task.get("detail") or "")[:500],
        "source_task_id": task["id"],
    }])
    if payload.get("idea_id"):
        reply_to_idea(payload["idea_id"], payload.get("reply", ""))
    return "書き方の決まりに足しました。次に作る記事から効きます。"


def do_rewrite_article(task: dict) -> str:
    """記事を書き直す。直したものは圭一郎さんの確認に戻す。"""
    payload = task.get("proposal_payload") or {}
    no = payload.get("article_no")
    if not no:
        raise RuntimeError("記事番号が分かりません")
    arts = sb("GET", f"articles?select=*&article_no=eq.{urllib.parse.quote(no)}")
    if not arts:
        raise RuntimeError(f"{no} が見つかりません")
    a = arts[0]

    # needs_fix のものは apply_fixes と同じ道を通す。
    # 「指示された箇所だけを直す」という制約をここでも守るため
    import apply_fixes
    if not (a.get("fix_note") or "").strip():
        raise RuntimeError("直す指示が空です")
    got = apply_fixes.revise(a, 600)
    revised = (got.get("revised") or "").strip()
    if not revised or revised == a["body_ai"]:
        raise RuntimeError("本文が変わりませんでした")

    holds = got.get("held") or []
    proposal = (got.get("proposal") or "").strip()
    if holds:
        question = "\n".join(f"・{h}" for h in holds)
        sb("PATCH", f"articles?article_no=eq.{urllib.parse.quote(no)}",
           {"status": "needs_owner_input",
            "revision_note": "いただいたご指示について、確認させてください。\n\n" + question})
        return f"{no} は直しきれず、圭一郎さんに聞き返しました。"

    sb("PATCH", f"articles?article_no=eq.{urllib.parse.quote(no)}",
       {"body_final": revised, "status": "revised", "revision_note": proposal or None})
    return f"{no} を直しました。圭一郎さんの確認まちです。"


def do_reschedule(task: dict) -> str:
    """投稿日を決め直す。見送りのものは承認済みに戻す。"""
    payload = task.get("proposal_payload") or {}
    no = payload.get("article_no")
    if not no:
        raise RuntimeError("記事番号が分かりません")
    # 承認済みに戻すだけ。実際の日取りは毎朝の schedule_posts.py が決める。
    # ここで日を決めると、他の予定との重なりを見られない
    sb("PATCH", f"articles?article_no=eq.{urllib.parse.quote(no)}",
       {"status": "approved", "scheduled_at": None})
    return f"{no} を投稿日の決め直しに回しました。翌朝の処理で日が決まります。"


def do_reply_only(task: dict) -> str:
    payload = task.get("proposal_payload") or {}
    if payload.get("idea_id"):
        reply_to_idea(payload["idea_id"], payload.get("reply", "") or task.get("proposal", ""))
        return "圭一郎さんにお返事しました。"
    return "返事の宛先が分からないため、何もしませんでした。"


HANDLERS = {
    "writing_rule": do_writing_rule,
    "rewrite_article": do_rewrite_article,
    "reschedule": do_reschedule,
    "reply_only": do_reply_only,
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

    tasks = sb("GET", "tasks?select=*&status=eq.approved&order=decided_at") or []
    if not tasks:
        logger.info("実行するやることはありません。")
        return 0
    logger.info(f"{len(tasks)}件を実行します")

    for t in tasks:
        kind = t.get("proposal_kind")
        logger.info(f"■ {t['title']}（{kind}）")
        if kind == "manual" or kind not in HANDLERS:
            logger.info("   人がやるものなので、ここでは何もしません")
            continue
        if args.dry_run:
            logger.info("   --dry-run のため実行しません")
            continue
        try:
            note = HANDLERS[kind](t)
            sb("PATCH", f"tasks?id=eq.{t['id']}",
               {"status": "done", "done_at": now(), "result_note": note})
            logger.info(f"   → {note}")
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            logger.error(f"   失敗: {msg[:160]}")
            sb("PATCH", f"tasks?id=eq.{t['id']}",
               {"result_note": f"実行に失敗しました。{msg[:300]}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
