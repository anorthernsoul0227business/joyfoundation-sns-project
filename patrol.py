#!/usr/bin/env python3
"""1日2回、見回って「やること」を見つけ、解決案を添える。

2026-09-08 康二郎さんの構想。それまで、圭一郎さんのメモは書き込まれるだけで
誰も見に行かず、9/4 のメモが4日間放置されていた。見落とす人がいる限り
「圭一郎さんと AI で完結」にはならないので、見回りを仕組みにする。

    /usr/bin/python3 patrol.py --dry-run
    /usr/bin/python3 patrol.py

## 見るところ

  ・返事をしていない思いつきメモ
  ・直しの依頼が来たまま動いていない記事
  ・AI が聞き返したまま返事がない記事
  ・見送りになっているが、まだ開催日に間に合う記事
  ・告知記事が1本も無い催し

## 案について

見つけたら AI が「こう解決します」という案を出す。承認されるまで何もしない。
実行できる種類（writing_rule / reschedule / rewrite_article / reply_only）に
当てはまらないものは manual とし、人がやることをはっきりさせる。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import announce_plan

logger = logging.getLogger("patrol")
JST = dt.timezone(dt.timedelta(hours=9))

# 承認を待たずに実行してよい種類（2026-09-28 康二郎さんの判断）。
# 「書き直す」は圭一郎さんの確認に戻るので、間違っていても世に出ない。
# 「投稿日を決め直す」は出す日が変わるだけ。「返事をする」は文章を送るだけ。
# writing_rule は今後の記事すべてに効くので承認を残す。manual は人がやるもの
AUTO_KINDS = {"rewrite_article", "reschedule", "reply_only"}

PROPOSAL_PROMPT = """あなたは、音による健康法を広める団体のSNS運用を任されている担当者です。
理事長（喜田圭一郎さん）から届いた内容に対して、どう対応するかの案を1つ考えてください。

## 届いた内容

種類: {source}
{detail}

## あなたが選べる対応

1. writing_rule … 記事の書き方の決まりとして残す。
   言葉づかい、使ってよい言い回し、避けるべき表現など、
   これからの記事すべてに効かせたいときに選びます。
2. rewrite_article … 特定の記事を書き直す。記事番号がはっきりしているときだけ。
3. reschedule … 投稿日を決め直す。記事番号（ART-0094 のような番号）が
   分かるときだけ選んでください。番号が書かれていない、どの記事か決められない
   ときは reply_only を選び、どの記事のことか尋ねてください。
   同じ日に告知が集中しているときは、動かす記事と移動先の日付を
   moves にすべて書いてください。1日に1件だけ残し、ほかを別の日へ散らします。
   開催日の前日に出す記事は動かさないでください（前日投稿は必ず守ります）。
   開催日より後には置かないでください。
4. reply_only … お礼や確認の返事をするだけでよいもの。
5. manual … 上のどれでもなく、人が手を動かす必要があるもの
   （写真の差し替え、外部サービスの設定など）。

## 出力

次の形のJSONだけを出力してください。前後に説明を書かないでください。

{{
  "title": "やることの見出し。15文字程度",
  "kind": "writing_rule / rewrite_article / reschedule / reply_only / manual のどれか",
  "proposal": "理事長と康二郎さんが読んで判断できるよう、何をするかを3〜5行で書く",
  "rule_body": "kind が writing_rule のとき、記事を書くAIに渡す決まりの文。
                「〜してください」「〜しないでください」の形で具体的に。それ以外は空文字",
  "article_no": "kind が rewrite_article / reschedule のとき、対象の記事番号
                 （例 ART-0094）。本文に書かれていなければ空文字",
  "want_date": "kind が reschedule で、希望の投稿日が示されているとき YYYY-MM-DD。
                示されていなければ空文字",
  "moves": "kind が reschedule で、複数の記事を動かすとき
            [{{\"article_no\": \"ART-0128\", \"want_date\": \"2026-10-20\"}}] の形で
            動かす記事ぶんすべて書く。1件だけなら空の配列 []",
  "reply": "理事長にお返しする言葉。ていねいに、専門用語を使わずに2〜4行"
}}

今日は {today} です。「来週」「1週間早く」のような言い方は、今日を起点に
実際の日付へ直してから書いてください。
"""


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
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:250]}") from e
        except Exception as e:
            last = e
            time.sleep(3 * (2 ** attempt))
    raise RuntimeError(f"Supabase に繋がりません: {last}")


def extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = text.find("{")
    if start < 0:
        raise ValueError("JSON が見つかりません")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("JSON が閉じていません")


def jst_date(iso: str) -> dt.date:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(JST).date()


# --- 見つける ---------------------------------------------------------------

def find_todos(today: dt.date) -> list[dict]:
    """やることを探す。source と source_key で重複を避ける。"""
    todos: list[dict] = []

    for i in sb("GET", "ideas?select=id,body,created_at&reply=is.null&order=created_at") or []:
        days = (today - jst_date(i["created_at"])).days
        todos.append({
            "source": "idea", "source_key": i["id"],
            "title": i["body"].splitlines()[0][:40],
            "detail": f"圭一郎さんの思いつきメモ（{days}日前）\n\n{i['body']}",
        })

    for a in sb("GET", "articles?select=article_no,platform,title,fix_note,status"
                       "&status=eq.needs_fix&order=article_no") or []:
        todos.append({
            "source": "fix_request", "source_key": a["article_no"],
            "title": f"{a['article_no']} の直しが止まっています",
            "detail": (f"記事 {a['article_no']}（{a['platform']}）「{a['title']}」に\n"
                       f"直しの依頼が来たまま動いていません。\n\n"
                       f"ご指示: {a.get('fix_note') or '(記載なし)'}"),
        })

    for a in sb("GET", "articles?select=article_no,platform,title,revision_note"
                       "&status=eq.needs_owner_input&order=article_no") or []:
        todos.append({
            "source": "owner_input", "source_key": a["article_no"],
            "title": f"{a['article_no']} で聞き返したまま",
            "detail": (f"記事 {a['article_no']}（{a['platform']}）「{a['title']}」について\n"
                       f"AI が聞き返したまま、返事がありません。\n\n"
                       f"聞いた内容: {a.get('revision_note') or '(記載なし)'}"),
        })

    for a in sb("GET", "articles?select=article_no,platform,title,event_date"
                       "&status=eq.missed&order=event_date") or []:
        if not a.get("event_date"):
            continue
        ev = dt.date.fromisoformat(a["event_date"])
        if announce_plan.plan_for(ev, today):
            todos.append({
                "source": "schedule", "source_key": a["article_no"],
                "title": f"{a['article_no']} はまだ間に合います",
                "detail": (f"記事 {a['article_no']}（{a['platform']}）「{a['title']}」は\n"
                           f"見送りになっていますが、開催は {ev}（あと{(ev - today).days}日）で\n"
                           f"まだ告知が間に合います。"),
            })

    # 未承認のイベント告知が同じ日に3件以上たまっていないか。
    # 2026-09-30 康二郎さん:「三件以上溜まったら注意喚起してください。
    # その時は投稿日時を考えましょう」
    pend = sb("GET", "articles?select=article_no,platform,scheduled_date,event_run_key,title"
                     "&status=in.(ai_draft,needs_check,staff_ok,revised,needs_owner_input)"
                     f"&event_date=not.is.null&scheduled_date=gte.{today.isoformat()}"
                     "&order=scheduled_date") or []
    byday: dict[str, list[dict]] = collections.defaultdict(list)
    for a in pend:
        byday[a["scheduled_date"]].append(a)
    for day, items in sorted(byday.items()):
        if len(items) < 3:
            continue
        names = "、".join(f"{a['article_no']}（{a['platform']}）" for a in items[:6])
        todos.append({
            "source": "schedule", "source_key": f"crowded:{day}",
            "title": f"{day} に未承認の告知が{len(items)}件たまっています",
            "detail": (f"{day} に投稿する予定の告知が {len(items)}件あり、"
                       f"いずれもまだ承認されていません。\n"
                       f"このまま承認されると同じ日に集中します。"
                       f"日をずらすか、一部を見送るかをご検討ください。\n\n"
                       f"対象: {names}"),
        })

    # 告知記事が1本も無い催し
    events = sb("GET", "events?select=series_run_key,title,starts_at,announce_skip,"
                       "articles_generated_at&order=starts_at") or []
    seen = set()
    for e in events:
        key = e.get("series_run_key")
        if not key or key in seen or e.get("announce_skip"):
            continue
        seen.add(key)
        day = jst_date(e["starts_at"])
        if day <= today or e.get("articles_generated_at"):
            continue
        todos.append({
            "source": "system", "source_key": f"noposts:{key}",
            "title": f"「{e['title'][:20]}」の告知がまだです",
            "detail": (f"{day}（あと{(day - today).days}日）の「{e['title']}」について、\n"
                       f"告知記事がまだ作られていません。"),
        })
    return todos


# --- 案を作る ---------------------------------------------------------------

def make_proposal(todo: dict, timeout: int, today: dt.date) -> dict:
    from run_weekly_loop import run_llm
    prompt = PROPOSAL_PROMPT.format(source=todo["source"], detail=todo["detail"],
                                    today=today.isoformat())
    out = run_llm(["claude", "-p", prompt, "--output-format", "text"],
                  f"解決案（{todo['source']}）", timeout, timeout + 300)
    text = out.stdout if hasattr(out, "stdout") else str(out)
    got = extract_json(text)
    kinds = {"writing_rule", "rewrite_article", "reschedule", "reply_only", "manual"}
    if got.get("kind") not in kinds:
        got["kind"] = "manual"
    return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
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
    orgs = sb("GET", "organizations?select=id&order=created_at.asc&limit=1")
    if not orgs:
        logger.error("organizations が空です")
        return 1
    org_id = orgs[0]["id"]

    todos = find_todos(today)
    logger.info(f"見回りで {len(todos)}件のやることを見つけました")

    # すでに登録済みのものは飛ばす。決着済み（done/dismissed）も作り直さない
    existing = {(t["source"], t["source_key"]): t
                for t in sb("GET", "tasks?select=source,source_key,status") or []}

    made = 0
    for todo in todos:
        key = (todo["source"], todo["source_key"])
        if key in existing:
            continue
        logger.info(f"■ {todo['title']}")
        try:
            got = make_proposal(todo, args.timeout, today)
        except Exception as e:
            logger.error(f"   案を作れませんでした: {type(e).__name__}: {e}")
            got = {"title": todo["title"], "kind": "manual",
                   "proposal": "案を作れませんでした。内容をご確認ください。", "reply": ""}
        auto = got["kind"] in AUTO_KINDS
        mark = "自動で進めます" if auto else "承認をお待ちします"
        logger.info(f"   → {got['kind']}（{mark}）: {got.get('proposal','')[:50]}")

        if args.dry_run:
            made += 1
            continue

        payload = {"reply": got.get("reply", "")}
        if got["kind"] == "writing_rule":
            payload["rule_body"] = got.get("rule_body", "")
            payload["scope"] = "both"
        # source_key が記事番号とはかぎらない。
        # 2026-09-30: 同じ日に集中した告知の source_key は "crowded:2026-10-18" で、
        # これを記事番号として渡していたため、7件が「記事が見つかりません」で失敗した。
        # （それ以前は0件の書き換えが黙って成功扱いになり、何もしていなかった）
        if todo["source"] in ("fix_request", "owner_input", "schedule"):
            key = todo["source_key"]
            if key.startswith("ART-"):
                payload["article_no"] = key
        if todo["source"] == "idea":
            payload["idea_id"] = todo["source_key"]
            # メモには記事番号が書かれていることがある（「ART-0094を…」）。
            # 2026-09-30: ここで拾っていなかったため、メモ由来の reschedule は
            # 必ず「記事番号が分かりません」で失敗していた。
            # 圭一郎さんの9/29の依頼2件が、誰にも知らされないまま止まっていた
            if got.get("article_no"):
                payload["article_no"] = got["article_no"].strip()
        if got.get("want_date"):
            payload["want_date"] = got["want_date"].strip()
        moves = [m for m in (got.get("moves") or [])
                 if isinstance(m, dict) and str(m.get("article_no", "")).startswith("ART-")]
        if moves:
            payload["moves"] = moves

        # 同じ日に集中している件は「注意喚起してください」というご依頼だった。
        # 何本もまとめて動かすのは、こちらの判断だけで進めるものではない
        if todo["source_key"].startswith("crowded:"):
            auto = False

        # 対象が分からない reschedule は動かしようがない。
        # 自動で進めて失敗を繰り返すより、承認待ちにして人の目に入れる
        if got["kind"] == "reschedule" and not (payload.get("article_no") or payload.get("moves")):
            logger.warning("   対象の記事が分からないので、自動では進めません")
            auto = False

        sb("POST", "tasks", body=[{
            "org_id": org_id,
            "source": todo["source"], "source_key": todo["source_key"],
            "title": got.get("title") or todo["title"],
            "detail": todo["detail"],
            "status": "approved" if auto else "proposed",
            "decided_at": dt.datetime.now(JST).isoformat() if auto else None,
            "decision_note": "元に戻せる内容のため、承認を待たずに進めました" if auto else None,
            "proposal": got.get("proposal", ""),
            "proposal_kind": got["kind"],
            "proposal_payload": payload,
        }])
        made += 1

    logger.info(f"完了: 新しく {made}件を登録しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
