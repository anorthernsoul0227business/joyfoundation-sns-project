#!/usr/bin/env python3
"""Evidenceカードの健全性を機械検証する。

このプロジェクトで実際に起きた事故を検出することが目的:
  - 原文にない数値の混入（例: 「HF成分 +23%」という原文に存在しない値）
  - 有意差がなかった項目の欠落（過大解釈の温床）
  - generalization_ng の未記入（一般化範囲を書けないカードは未完成）

原文は2段組PDF由来で列がインターリーブされるため、行単位の部分一致は使えない。
代わりに「数値トークンが原文に実在するか」を照合する。捏造は必ずここに現れる。

使い方:
    python3 knowledge/verify_cards.py
終了コード 0=合格 / 1=要修正
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "knowledge" / "evidence"
EXTRACT = ROOT / "knowledge" / "_extract"

# 数値トークン: 小数・カンマ区切り・パーセント等を1トークンとして拾う
NUM = re.compile(r"\d+(?:[.,]\d+)*")
# 照合から除外する自明な値（章番号・箇条書き番号などノイズが多い）
TRIVIAL = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "0"}


def norm(s: str) -> str:
    """全角/半角・空白・先頭ゼロの揺れを吸収する。

    原文PDFの統計表は1文字ずつスペース区切りで出力される（`. 8 5`）ため空白を全除去し、
    さらに `.85` と `0.85` を同一視する（SPSS出力は先頭ゼロを省略するがカードでは補うため）。
    """
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))
    return re.sub(r"(?<![\d.])\.(\d)", r"0.\1", s)


def in_corpus(num: str, corpus: str) -> bool:
    """数値トークンが原文に実在するか判定する。

    原文の統計表は1文字ずつスペース区切りのため、空白除去すると隣接する列同士が
    連結する（`29` + `.000` → `29.000`）。そのため先頭ゼロを外した形でも照合する。
    厳密な証明ではなく捏造検出のためのガードであり、短い値では取りこぼしうる。
    """
    return num in corpus or (num.startswith("0.") and num[1:] in corpus)


def block(text: str, key: str) -> str:
    """YAMLフロントマターから `key: |` ブロックを取り出す。"""
    m = re.search(rf"^{key}:\s*\|\s*$(.*?)^\w[\w_]*:", text, re.S | re.M)
    return m.group(1) if m else ""


def field(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def main() -> int:
    if not EXTRACT.is_dir():
        print("原文ディレクトリ knowledge/_extract/ がありません。")
        print("PDFから抽出してください: pdftotext -layout <pdf> knowledge/_extract/<name>.txt")
        return 1

    corpus = norm(
        "".join(
            p.read_text(encoding="utf-8", errors="replace") for p in EXTRACT.glob("*.txt")
        )
    )

    failed = False
    for card in sorted(EVID.glob("EV-*.md")):
        text = card.read_text(encoding="utf-8")
        problems = []

        # --- 1. verbatim 内の数値が原文に実在するか ---
        vb = block(text, "verbatim")
        if not vb.strip():
            problems.append("verbatim が空")
        else:
            ghosts = sorted(
                {n for n in NUM.findall(norm(vb)) if n not in TRIVIAL and not in_corpus(n, corpus)}
            )
            if ghosts:
                problems.append(f"原文にない数値: {', '.join(ghosts)}")

        # --- 2. findings 内の value も同様に照合 ---
        for val in re.findall(r'^\s*value:\s*"(.+)"\s*$', text, re.M):
            ghosts = sorted(
                {n for n in NUM.findall(norm(val)) if n not in TRIVIAL and not in_corpus(n, corpus)}
            )
            if ghosts:
                problems.append(f"findings.value に原文にない数値: {', '.join(ghosts)}")

        # --- 3. 有意差なしの記録があるか ---
        # 原文が「変化がなかった」「有意な差はみられなかった」等と述べているのに
        # significant: false が1つもない場合は取りこぼしの疑い
        no_effect_in_source = re.search(r"変化がなかった|有意な差(?:は)?み?られな|差はな", norm(vb))
        if no_effect_in_source and "significant: false" not in text:
            problems.append("原文に「変化なし」の記述があるが significant: false が無い")

        # --- 4. generalization_ng は必須 ---
        if not block(text, "generalization_ng").strip():
            problems.append("generalization_ng が空（一般化範囲を書けないカードは使用不可）")

        # --- 5. 承認されていないカードが active になっていないか ---
        status = field(text, "status")
        approvals = re.search(
            r"^approval:\s*$\n\s*transcription:\s*(\S+)\s*.*?\n\s*interpretation:\s*(\S+)\s*.*?\n\s*publication:\s*(\S+)",
            text,
            re.M | re.S,
        )
        if status == "active" and approvals and "未" in approvals.groups():
            problems.append("status: active だが approval に未承認が残っている")

        # --- 6. source_file が実在するか ---
        src = field(text, "source_file")
        if src and not (ROOT / src).exists():
            problems.append(f"source_file が存在しない: {src}")

        if problems:
            failed = True
            print(f"NG {card.name}")
            for p in problems:
                print(f"     ⚠ {p}")
        else:
            print(f"OK {card.name}")

    print()
    if failed:
        print("要修正のカードがあります。")
        return 1
    print("全カード合格。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
