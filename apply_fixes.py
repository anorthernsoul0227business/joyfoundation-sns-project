#!/usr/bin/env python3
"""圭一郎さんの修正依頼を AI が本文に反映する。

共有ボードで「直したいところがある」と書かれた記事（status=needs_fix）を拾い、
指示どおりに本文を直し、自動検証にかけたうえで status=revised に進める。
圭一郎さんの画面には「直す前／直した後」が並んで出る。

    /usr/bin/python3 apply_fixes.py --dry-run      # 直した結果を表示するだけ
    /usr/bin/python3 apply_fixes.py --only ART-0049
    /usr/bin/python3 apply_fixes.py                # 反映する

設計の前提（2026-09-02 康二郎さん）:
  最終的に康二郎さんはこの輪に入らない。圭一郎さんと AI だけで完結させる。
  そのため AI は「指示に無いことをしない」ことを最優先にし、
  判断に迷ったら勝手に書き換えず、理由を添えて保留する。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger("apply_fixes")

PLATFORM_JA = {"x": "X", "ig": "Instagram", "note": "note", "youtube": "YouTube", "line": "LINE"}

# 指示に無い書き換えを防ぐため、守ってほしいことを明示する
PROMPT = """あなたは、ある団体のSNS記事を編集する担当者です。

理事長（喜田圭一郎さん）から、下の記事について修正の指示が届きました。
指示のとおりに本文を直してください。

## 最も大切なこと

- **指示された箇所だけを直してください。** 指示に無い部分は、言い回しも改行も
  一字も変えないでください。良かれと思って整えることもしないでください。
- 指示が曖昧で、直し方が一通りに定まらない場合は、**直さずに保留**してください。
- 指示が「削除してください」であれば、その文を消して前後が自然に繋がるようにしてください。
  そのために必要な最小限の調整（句点や接続の調整）はして構いません。
- 新しい事実・数値・出典を、あなたの判断で足さないでください。
  ただし**指示の中に書かれている内容**であれば、そのまま使って構いません。

## 字数が収まらない場合

{platform} は {limit} です。X の140字は投稿できるかどうかの絶対条件です。

指示どおり直すと字数に収まらないときは、**あなたの判断で勝手に縮めないでください。**
代わりに、収めるための案を1つだけ考え、"proposal" に書いてください。
"revised" には**その案を適用した本文**を入れ、何をどう変えたかを必ず "proposal" で説明します。
理事長がそれを読んで、承諾するか言い直すかを決めます。

案は、意味が変わらず、最も小さい変更を選んでください
（例:「約15分」→「15分」、重複した語の削除）。

## 直す前の本文

{body}

## 理事長からの指示

{note}

## 出力

次の形のJSONだけを出力してください。前後に説明を書かないでください。

{{
  "revised": "直した後の本文の全文",
  "applied": ["適用した指示を一つずつ短く"],
  "held": ["直さずに保留した指示と、その理由"],
  "proposal": "字数のために指示以外の箇所を変えた場合、理事長に宛てて『字数が◯字超えたため、△△を□□にしました。これでよろしいですか。』のように書く。変えていなければ空文字"
}}

保留が無ければ "held" は空の配列にしてください。
"""

LIMITS = {
    "x": "140字以内",
    "ig": "400〜600字",
    "note": "1,500〜2,500字",
    "youtube": "説明文",
    "line": "短文",
}


def sb(method: str, path: str, body=None):
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY がありません")
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
        method=method,
    )
    for h, v in [("apikey", key), ("Authorization", f"Bearer {key}"),
                 ("Content-Type", "application/json"), ("Prefer", "return=representation")]:
        req.add_header(h, v)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else None


def extract_json(text: str) -> dict:
    """LLM の出力から JSON を取り出す。前後に説明が付くことがある。"""
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


def revise(article: dict, timeout: int) -> dict:
    from run_weekly_loop import run_llm
    prompt = PROMPT.format(
        platform=PLATFORM_JA.get(article["platform"], article["platform"]),
        limit=LIMITS.get(article["platform"], ""),
        body=article["body_ai"],
        note=article["fix_note"],
    )
    out = run_llm(["claude", "-p", prompt, "--output-format", "text"],
                  f"修正の反映（{article['article_no']}）", timeout, timeout + 300)
    text = out.stdout if hasattr(out, "stdout") else str(out)
    return extract_json(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="表示するだけで反映しない")
    ap.add_argument("--only", help="記事番号を指定して1件だけ処理する")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    q = "articles?select=*&status=eq.needs_fix&order=article_no"
    if args.only:
        q += f"&article_no=eq.{args.only}"
    targets = [a for a in (sb("GET", q) or []) if (a.get("fix_note") or "").strip()]
    if not targets:
        logger.info("直す依頼はありません。")
        return 0
    logger.info(f"{len(targets)}件の修正依頼を処理します")

    from run_weekly_loop import load_cards, verify

    cmap = {c["id"]: c for c in load_cards(allow_draft=True)}
    ok = held = failed = 0

    for a in targets:
        ano = a["article_no"]
        logger.info(f"--- {ano}（{PLATFORM_JA.get(a['platform'])}, {len(a['body_ai'])}字）")
        try:
            got = revise(a, args.timeout)
        except Exception as e:
            logger.error(f"  失敗: {type(e).__name__}: {str(e)[:160]}")
            failed += 1
            continue

        revised = (got.get("revised") or "").strip()
        applied, holds = got.get("applied") or [], got.get("held") or []
        proposal = (got.get("proposal") or "").strip()
        for x in applied:
            logger.info(f"  適用: {x}")
        for x in holds:
            logger.warning(f"  保留: {x}")
        if proposal:
            logger.info(f"  申し送り: {proposal}")

        if not revised:
            logger.error("  本文が空です。とばします")
            failed += 1
            continue
        if revised == a["body_ai"]:
            logger.warning("  本文が変わっていません。とばします")
            held += 1
            continue

        # 直した結果にも自動検証をかける（根拠にない数値が増えていないか）
        post = {"本文": revised, "媒体": PLATFORM_JA.get(a["platform"], ""),
                "使用カードID": a.get("source_card_ids") or []}
        before = verify({"本文": a["body_ai"], "媒体": post["媒体"],
                         "使用カードID": post["使用カードID"]}, cmap)
        after = verify(post, cmap)
        new_problems = [p for p in after["problems"] if p not in before["problems"]]
        for p in after["problems"]:
            mark = "新" if p in new_problems else "既"
            logger.warning(f"  検証[{mark}]: {p}")

        logger.info(f"  {len(a['body_ai'])}字 → {len(revised)}字")
        if args.dry_run:
            print("\n" + "=" * 60 + f"\n{ano} 直した後\n" + "=" * 60)
            print(revised + "\n")
            continue

        # 保留があるうちは圭一郎さんに戻さない（指示が伝わっていないため）
        if holds:
            logger.warning("  保留があるので needs_fix のままにします")
            held += 1
            continue

        # 字数を超えたまま渡すと投稿できない。案が無い場合は戻さない
        if new_problems and not proposal:
            logger.warning("  新しい問題があるのに案が無いので needs_fix のままにします")
            held += 1
            continue

        sb("PATCH", f"articles?article_no=eq.{ano}",
           {"body_final": revised, "status": "revised", "revision_note": proposal or None})
        logger.info("  → 「直しました（確認まち）」にしました"
                    + ("／申し送りあり" if proposal else ""))
        ok += 1

    logger.info(f"完了: 反映 {ok}件 / 保留 {held}件 / 失敗 {failed}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
