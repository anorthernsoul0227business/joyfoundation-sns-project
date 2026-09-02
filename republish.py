#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""シート投入に失敗した生成物を、退避ファイルから復旧する。

週次ループはネットワークエラー等でシート書き込みに失敗すると、
生成物を `logs/unpublished_*.json` に退避して終了する。
記事の生成には10〜15分かかるため、捨てずに復旧できるようにしてある。

退避ファイルがない場合（古い実行分など）は、`logs/revised_*.txt` または
`logs/generated_*.txt` からも復旧できる。

実行:
    /usr/bin/python3 republish.py                                  # 退避ファイルを探して復旧
    /usr/bin/python3 republish.py logs/unpublished_20260801_094701.json
    /usr/bin/python3 republish.py logs/revised_20260801_094701.txt --test-cards
"""

import argparse
import json
import re
import sys
from pathlib import Path

import gspread

from run_weekly_loop import LOGDIR, ROOT, load_cards, publish, verify


def load_posts(path: Path, test_cards: bool):
    """退避JSON / 生成テキスト のどちらからでも読めるようにする。"""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        d = json.loads(text)
        return d["posts"], d.get("reviews", []), d.get("test_mode", test_cards)
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.S) or re.search(r"(\[.*\])", text, re.S)
    if not m:
        raise ValueError("JSONを取り出せませんでした")
    return json.loads(m.group(1)), [], test_cards


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="退避ファイル。省略時は最新の unpublished_*.json")
    ap.add_argument("--test-cards", action="store_true",
                    help="未承認カードを使った生成物として扱う（テキストから復旧する場合）")
    args = ap.parse_args()

    if args.path:
        path = Path(args.path)
    else:
        cands = sorted(LOGDIR.glob("unpublished_*.json"))
        if not cands:
            print("退避ファイルが見つかりません（logs/unpublished_*.json）")
            print("生成テキストから復旧する場合はパスを指定してください:")
            print("  /usr/bin/python3 republish.py logs/revised_XXXX.txt --test-cards")
            return 1
        path = cands[-1]
    if not path.exists():
        print(f"ファイルがありません: {path}")
        return 1

    posts, reviews, test_mode = load_posts(path, args.test_cards)
    print(f"{path.name} から {len(posts)}本を読み込みました（test_mode={test_mode}）")

    cmap = {c["id"]: c for c in load_cards(allow_draft=True)}
    results = [verify(p, cmap) for p in posts]
    for p, r in zip(posts, results):
        mark = "○" if not r["problems"] else "△"
        print(f"  {mark} {p.get('媒体','?'):10} {r['grade'].split(':')[0]} {len(p.get('本文',''))}字")
        for x in r["problems"]:
            print(f"       - {x}")

    # publish() は共有ボード（Supabase）へ書くので、先に .env を読む
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    gc = gspread.service_account()
    n = publish(gc, posts, results, reviews, test_mode)
    print(f"\n共有ボードに {n}件を復旧しました")

    if path.suffix == ".json":
        done = path.with_suffix(".json.done")
        path.rename(done)
        print(f"退避ファイルを {done.name} にリネームしました（二重投入の防止）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
