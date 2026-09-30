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


def move_one(no: str, want: str | None) -> str:
    """記事1本の投稿日を変える。希望日が無ければ翌朝の処理にまかせる。"""
    got = sb("GET", f"articles?select=article_no,event_date,announce_role"
                    f"&article_no=eq.{urllib.parse.quote(no)}") or []
    if not got:
        raise RuntimeError(f"{no} という記事が見つかりません")
    a = got[0]

    if not want:
        # 実際の日取りは毎朝の schedule_posts.py が決める。
        # ここで日を決めると、他の予定との重なりを見られない
        sb("PATCH", f"articles?article_no=eq.{urllib.parse.quote(no)}",
           {"status": "approved", "scheduled_at": None})
        return f"{no} を投稿日の決め直しに回しました"

    # 2026-09-30: 圭一郎さんが「9月30日に投稿してください」と日を指定されても、
    # 受け取る口が無く、翌朝の処理が勝手に日を決め直していた
    try:
        day = dt.date.fromisoformat(want)
    except ValueError as e:
        raise RuntimeError(f"{no}: 希望日が読めません（{want}）") from e
    if day < dt.datetime.now(JST).date():
        raise RuntimeError(f"{no}: 希望日 {day} はもう過ぎています")
    ev = a.get("event_date")
    if ev and day >= dt.date.fromisoformat(ev):
        raise RuntimeError(f"{no}: 希望日 {day} は開催日 {ev} より後です")
    # 前日投稿は動かさない（2026-09-04 に圭一郎さんと決めた絶対の決まり）
    if a.get("announce_role") == "day_before":
        raise RuntimeError(f"{no} は開催の前日に出す記事なので動かせません")

    sb("PATCH", f"articles?article_no=eq.{urllib.parse.quote(no)}",
       {"status": "approved", "scheduled_at": None, "scheduled_date": day.isoformat()})
    return f"{no} を {day} へ"


def do_reschedule(task: dict) -> str:
    """投稿日を決め直す。1本でも、同じ日に集中したぶんをまとめてでも。"""
    payload = task.get("proposal_payload") or {}

    # 同じ日に集中した告知を散らす場合は、動かす記事が複数ある
    moves = payload.get("moves") or []
    if moves:
        done = [move_one(str(m["article_no"]).strip(), (m.get("want_date") or "").strip() or None)
                for m in moves]
        return "、".join(done) + " に変えました。翌朝の処理でキューに入ります。"

    no = payload.get("article_no")
    if not no:
        raise RuntimeError("記事番号が分かりません")
    return move_one(no, (payload.get("want_date") or "").strip() or None) + \
        "。翌朝の処理でキューに入ります。"


def do_reply_only(task: dict) -> str:
    """お返事をする。宛先はメモか、記事の画面か。"""
    payload = task.get("proposal_payload") or {}
    text = (payload.get("reply") or "").strip() or (task.get("proposal") or "").strip()
    if not text:
        raise RuntimeError("お返しする文章が空です")

    if payload.get("idea_id"):
        reply_to_idea(payload["idea_id"], text)
        return "思いつきメモにお返事しました。"

    # 記事から来たタスクは、その記事の画面でお尋ねする。
    # 2026-09-28: 宛先が無いとして何もしていなかった。
    # 記事についての問い合わせなのだから、記事の画面に出すのが自然
    no = payload.get("article_no")
    if no:
        sb("PATCH", f"articles?article_no=eq.{urllib.parse.quote(no)}",
           {"status": "needs_owner_input", "revision_note": text})
        return f"{no} の画面で圭一郎さんにお尋ねしました。"

    raise RuntimeError("返事の宛先が分かりません")


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

    failed: list[tuple[dict, str]] = []
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
            # 失敗したものは承認まちに戻す。
            # 2026-09-30: approved のまま置いたため、見回りのたびに同じ失敗を
            # くり返し、同じ知らせが1日2回届いていた。
            # 承認まちにすれば画面に出るし、勝手に動き続けることもない
            sb("PATCH", f"tasks?id=eq.{t['id']}",
               {"status": "proposed", "decided_at": None,
                "result_note": f"実行に失敗しました。{msg[:300]}"})
            failed.append((t, msg))

    # 失敗は黙って置いておかない。
    # 2026-09-30: 圭一郎さんの依頼2件が「記事番号が分かりません」で失敗したまま、
    # 見回りのたびに同じ失敗を繰り返し、誰にも知らされていなかった。
    # 承認まで済んでいる以上、止まっていることは人に伝わらなければならない
    if failed:
        try:
            import line_channel
            line_channel.notify_line(
                f"⚠ やることの実行に失敗しました（{len(failed)}件）",
                "\n".join(f"・{t['title']}\n　{m[:70]}" for t, m in failed),
                "https://shc-sns-calendar-web.vercel.app/board")
        except Exception as e:
            logger.error(f"失敗の連絡ができませんでした: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
