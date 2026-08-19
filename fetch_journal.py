#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""協会誌（サウンドヒーリング協会 公式サイト）の本文を取得して保存する。

理事長メッセージは Voice カードの主要な材料。Evidence カード（学会発表）だけで
書くと毎回研究の話になるため、思想・言葉の層をここから供給する。

`資料まとめ.md` にも協会誌の内容が入っているが、あちらは要約であり
逐語ではない。Voice カードの `verbatim` には使えないので、原本から取り直す。

    /usr/bin/python3 fetch_journal.py           # 全号
    /usr/bin/python3 fetch_journal.py --list    # 対象URLの一覧だけ
"""

import argparse
import html
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "docs" / "sources" / "協会誌"
BASE = "https://www.sound-healing.jp/aj/aj_vol{}.html"

# 公開されている号（レポートページの記載より）
VOLS = ["20-21", "22-23", "24-25", "26-27", "28-29", "30-31", "32-33", "33-34",
        "35-36", "37-38", "39-40"]

# 全ページ共通のナビゲーション。本文ではないので落とす
NAV = {
    "協会について", "設立趣旨", "理事一覧", "定款", "3つの提案", "自然音", "体感音響",
    "呼吸と声", "活動内容", "資格認定研修会", "ファシリテーター", "セラピスト",
    "ウエルビーイングクリエイター", "レポート", "会員制度", "お問い合わせ",
    "サウンドヒーリング協会The Society for Harmonic Science", "HOME", "ホーム",
    "個人情報保護方針", "サイトマップ", "ページトップへ", "Harmonic Day",
    "サウンドヒーリング研究会", "入会のご案内", "リンク",
}


def strip_html(raw: bytes) -> str:
    for enc in ("utf-8", "shift_jis", "euc-jp"):
        try:
            s = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        s = raw.decode("utf-8", "replace")

    s = re.sub(r"(?is)<(script|style|head).*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h[1-6]>|</li>|</tr>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)

    out, seen_body = [], False
    for line in s.splitlines():
        line = line.strip()
        if not line or line in NAV:
            continue
        # 「協会誌 vol.」が出たところから本文とみなす
        if not seen_body and "協会誌" in line:
            seen_body = True
        if seen_body:
            out.append(line)
    return "\n".join(out) if out else "\n".join(
        l.strip() for l in s.splitlines() if l.strip() and l.strip() not in NAV)


def fetch(vol: str) -> str:
    url = BASE.format(vol)
    p = subprocess.run(["curl", "-sL", "--max-time", "40", url],
                       capture_output=True, timeout=60)
    if p.returncode != 0 or len(p.stdout) < 2000:
        raise RuntimeError(f"取得できません（{len(p.stdout)}バイト）")
    return strip_html(p.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for v in VOLS:
            print(" ", BASE.format(v))
        return

    DEST.mkdir(parents=True, exist_ok=True)
    ok = ng = 0
    for v in VOLS:
        dest = DEST / f"aj_vol{v}.md"
        try:
            body = fetch(v)
        except Exception as e:
            print(f"  ✗ vol.{v}: {type(e).__name__}: {e}")
            ng += 1
            continue
        head = (f"---\nsource: 協会誌 vol.{v}\n"
                f"url: {BASE.format(v)}\n"
                f"fetched_at: 2026-08-18\n"
                f"method: 公式サイトのHTMLからタグを除去（要約していない）\n"
                f"note: 共通ナビゲーションは除外。図版・PDF内の内容は含まない\n---\n\n")
        dest.write_text(head + body + "\n", encoding="utf-8")
        n = len(body)
        print(f"  ✓ vol.{v}  {n:,}字  → {dest.name}")
        ok += 1
        time.sleep(1.5)     # 相手のサーバーに負荷をかけない

    print(f"\n取得 {ok}号 / 失敗 {ng}号  → {DEST}")


if __name__ == "__main__":
    main()
