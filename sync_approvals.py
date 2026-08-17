#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【退役】カード単位の事前承認をシートから取り込むスクリプト。

2026-08-17 に承認方式を「カードの事前承認」から「完成投稿への承認」へ変更した。
参照していた `週次_カード承認` タブは削除済みで、このスクリプトは動かない。

後継: extract_ac.py（圭一郎さんがOKした投稿から AC カードを切り出す）

残してある理由は、`detect_conflict()` の実装（原本の数値と食い違う修正、
原文の書き換えを検出して ESC を起こす）が再利用しうるため。
バックアップ: docs/sheet_backup_20260817/週次_カード承認.json
"""

import sys

print(__doc__, file=sys.stderr)
print("このスクリプトは退役しました。extract_ac.py を使ってください。", file=sys.stderr)
sys.exit(1)

# ===== 以下、旧実装（参照用。実行されない） =====

import argparse
import re
import sys
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import gspread

ROOT = Path(__file__).resolve().parent
EVID = ROOT / "knowledge" / "evidence"
EXTRACT = ROOT / "knowledge" / "_extract"
ESCALATION = ROOT / "knowledge" / "escalation.md"

NUM = re.compile(r"\d+(?:[.,]\d+)*")
TRIVIAL = {str(i) for i in range(10)}

SPREADSHEET_KEY = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
TAB_CARDS = "週次_カード承認"

# シートのプルダウン値 → カードの approval 値
DECISION = {
    "承認する": "済",
    "要修正（コメント欄に記入）": "要修正",
    "保留・判断できない": "保留",
    "": None,   # 未記入は変更しない
}

COL = {   # 0始まりの列インデックス
    "id": 0,
    "interpretation": 8,
    "publication": 9,
    "comment": 10,
    "reviewer": 11,
    "approved_at": 12,
}


def set_approval(text: str, key: str, value: str) -> str:
    """approval ブロック内の 1 キーだけを書き換える。"""
    pattern = re.compile(
        rf"(^approval:\s*$(?:\n(?!\w).*)*?\n\s+{key}:\s*)(\S+)([^\n]*)",
        re.M,
    )
    return pattern.sub(lambda m: f"{m.group(1)}{value}", text, count=1)


def set_scalar(text: str, key: str, value: str) -> str:
    """フロントマターのトップレベル スカラーを書き換える。"""
    return re.sub(rf"^({key}:\s*).*$", lambda m: f"{m.group(1)}{value}", text, count=1, flags=re.M)


def load_corpus() -> str:
    """原本の抽出テキストを1本に連結して正規化する。"""
    if not EXTRACT.is_dir():
        return ""
    raw = "".join(
        p.read_text(encoding="utf-8", errors="replace") for p in EXTRACT.glob("*.txt")
    )
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", raw))
    return re.sub(r"(?<![\d.])\.(\d)", r"0.\1", s)


def _norm(s: str) -> str:
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))
    return re.sub(r"(?<![\d.])\.(\d)", r"0.\1", s)


def _has_number(num: str, text: str) -> bool:
    """数値が「独立したトークンとして」原文に存在するか。

    空白を全除去すると隣接する数値が連結して偽の一致を生む（`図8` + `8.8` → `88.8`）。
    前後が数字・小数点でないことを確認して桁の食い込みを防ぐ。
    """
    return re.search(rf"(?<![\d.]){re.escape(num)}(?![\d])", text) is not None


def detect_conflict(card_text: str, comment: str, corpus: str) -> str:
    """修正指示が原本と食い違っていないか判定し、理由を返す（問題なければ空文字）。

    Evidence カードの verbatim は原本PDFと機械照合済みなので、
    原本と異なる内容への修正指示は必ず食い違いであり、カードを書き換えてはいけない。

    2つの規則で検出する:
      A. 原本のどこにも存在しない数値が含まれている
      B. verbatim の一節をわずかに変えた文が含まれている（＝原文そのものの改変提案）
         1桁の違い（9例→8例）は規則Aでは捕まらないため、こちらで拾う。
    """
    if not comment.strip():
        return ""

    # --- 規則A: 原本に存在しない数値 -------------------------------------
    if corpus:
        ghosts = sorted({
            n for n in NUM.findall(_norm(comment))
            if n not in TRIVIAL and not _has_number(n, corpus)
        })
        if ghosts:
            return f"原本のどこにも存在しない数値が含まれています: {', '.join(ghosts)}"

    # --- 規則B: verbatim の改変提案 --------------------------------------
    m = re.search(r"^verbatim:\s*\|\s*$(.*?)^\w[\w_]*:", card_text, re.S | re.M)
    if not m:
        return ""
    vb_lines = [_norm(ln) for ln in m.group(1).splitlines() if len(_norm(ln)) >= 12]
    if not vb_lines:
        return ""

    for raw in comment.splitlines():
        cand = _norm(raw)
        if len(cand) < 12 or any(cand in v or v in cand for v in vb_lines):
            continue   # 完全一致・包含は「引用しただけ」なので問題なし
        for v in vb_lines:
            ratio = SequenceMatcher(None, cand, v).ratio()
            if ratio >= 0.80:   # よく似ているが同一ではない = 原文の書き換え提案
                diff = [
                    f"「{v[i1:i2]}」→「{cand[j1:j2]}」"
                    for tag, i1, i2, j1, j2 in SequenceMatcher(None, v, cand).get_opcodes()
                    if tag == "replace"
                ]
                detail = "、".join(diff[:3]) if diff else "（差分の特定に失敗）"
                return f"原文（verbatim）の書き換えを求めています: {detail}"
    return ""


def next_esc_id() -> str:
    text = ESCALATION.read_text(encoding="utf-8") if ESCALATION.exists() else ""
    nums = [int(m) for m in re.findall(r"^## ESC-(\d+)", text, re.M)]
    return f"ESC-{max(nums) + 1 if nums else 1:03d}"


def raise_escalation(esc_id: str, card_id: str, reason: str, comment: str,
                     who: str, when: str) -> str:
    """エスカレーション項目の本文を組み立てる。"""
    return f"""
---

## {esc_id} — {card_id} の修正指示が原本と一致しない

- **起票日:** {when}
- **関連カード:** [{card_id}](evidence/{card_id}.md)
- **状態:** 🔴 未解決
- **優先度:** 高
- **起票:** `sync_approvals.py` が自動検出（{who} の修正指示）

### 何が食い違っているか

**{reason}**

Evidence カードの `verbatim` は原本PDFと機械照合済みです。
そのため、この修正をそのまま適用すると原本と矛盾したカードになります。

修正指示の全文:

```
{comment.strip()}
```

### 考えられる解釈

1. 別の資料・別の研究を指している（取り違え）
2. 記憶違い
3. 原本自体に誤りがあり、正誤表や改訂版が存在する

### 確認したいこと

1. この数値は**どの資料**に記載されているものでしょうか
2. 原本（`{card_id}` の `source_file`）とは別の資料という理解で合っていますか

### 解決するまでの扱い

- {card_id} は `disputed`。承認は反映せず、記事生成にも使用しない
"""


def append_note(text: str, when: str, who: str, body: str) -> str:
    """本文末尾にレビューコメントを追記する（上書きしない）。"""
    header = "## レビューコメント"
    entry = f"\n### {when} {who}\n\n{body.strip()}\n"
    if header in text:
        return text.rstrip() + "\n" + entry
    return text.rstrip() + f"\n\n---\n\n{header}\n" + entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="カードに実際に書き込む")
    args = ap.parse_args()

    gc = gspread.service_account()
    ws = gc.open_by_key(SPREADSHEET_KEY).worksheet(TAB_CARDS)
    rows = ws.get_all_values()[1:]   # ヘッダーを除く

    corpus = load_corpus()
    if not corpus:
        print("警告: knowledge/_extract/ が空です。原本との矛盾検出が無効になります。\n")

    today = date.today().isoformat()
    changed = skipped = escalated = 0
    new_escalations = []

    for row in rows:
        row = row + [""] * (13 - len(row))       # 末尾の空セルは省略されるため埋める
        card_id = row[COL["id"]].strip()
        if not card_id:
            continue

        path = EVID / f"{card_id}.md"
        if not path.exists():
            print(f"?? {card_id}: カードファイルが見つかりません")
            continue

        text = original = path.read_text(encoding="utf-8")

        if re.search(r"^status:\s*disputed", text, re.M):
            if any(row[COL[k]].strip() for k in ("interpretation", "publication")):
                print(f"-- {card_id}: disputed のため反映しません（ESC の解決が先）")
                skipped += 1
            continue

        reviewer_name = row[COL["reviewer"]].strip() or "（記名なし）"
        raw_comment = row[COL["comment"]].strip()

        # --- 原本と矛盾する修正指示は反映せずエスカレーションする ---------
        conflict = detect_conflict(text, raw_comment, corpus) if raw_comment else ""
        if conflict:
            esc_id = next_esc_id() if not new_escalations else \
                f"ESC-{int(next_esc_id().split('-')[1]) + len(new_escalations):03d}"
            when = row[COL["approved_at"]].strip() or today
            new_escalations.append(
                raise_escalation(esc_id, card_id, conflict, raw_comment, reviewer_name, when)
            )
            text = set_scalar(text, "status", "disputed")
            if not re.search(r"^escalation:", text, re.M):
                text = re.sub(r"^(status:\s*disputed[^\n]*)$",
                              rf"\1\nescalation: {esc_id}", text, count=1, flags=re.M)
            text = append_note(text, when, reviewer_name,
                               f"⚠ {conflict}\n\n{esc_id} として起票し、反映を保留しました。\n\n{raw_comment}")
            escalated += 1
            print(f"!! {card_id}: {conflict}\n     → {esc_id} を起票し disputed に変更（承認は反映しません）")
            if args.apply:
                path.write_text(text, encoding="utf-8")
            changed += 1
            continue

        notes = []
        for key in ("interpretation", "publication"):
            raw = row[COL[key]].strip()
            value = DECISION.get(raw, raw or None)
            if value is None:
                continue
            current = re.search(rf"^\s+{key}:\s*(\S+)", text, re.M)
            if current and current.group(1) == value:
                continue
            text = set_approval(text, key, value)
            notes.append(f"{key}: {current.group(1) if current else '?'} → {value}")

        reviewer = row[COL["reviewer"]].strip()
        approved_at = row[COL["approved_at"]].strip() or (today if notes else "")
        if notes:
            if reviewer:
                text = set_scalar(text, "reviewer", reviewer)
            if approved_at:
                text = set_scalar(text, "approved_at", approved_at)

        # 解釈・公開の両方が「済」になったら active に上げる
        appr = re.search(
            r"^approval:\s*$\n\s+transcription:\s*(\S+).*?\n\s+interpretation:\s*(\S+).*?\n\s+publication:\s*(\S+)",
            text, re.M | re.S,
        )
        if appr and all(v == "済" for v in appr.groups()):
            if not re.search(r"^status:\s*active", text, re.M):
                text = set_scalar(text, "status", "active")
                notes.append("status: → active（記事生成に使用可）")

        if raw_comment and raw_comment not in text:
            text = append_note(text, approved_at or today, reviewer_name, raw_comment)
            notes.append("コメントを追記")

        if text == original:
            continue

        changed += 1
        print(f"** {card_id}")
        for n in notes:
            print(f"     {n}")
        if args.apply:
            path.write_text(text, encoding="utf-8")

    if new_escalations and args.apply:
        base = ESCALATION.read_text(encoding="utf-8") if ESCALATION.exists() else "# エスカレーション一覧\n"
        marker = "## 記入フォーマット（新規起票時）"
        body = "".join(new_escalations)
        if marker in base:
            head, tail = base.split(marker, 1)
            base = head.rstrip() + "\n" + body + "\n---\n\n" + marker + tail
        else:
            base = base.rstrip() + "\n" + body
        ESCALATION.write_text(base, encoding="utf-8")

    print()
    if not changed and not skipped:
        print("反映すべき変更はありません（シートが未記入か、既に反映済み）。")
        return 0

    print(f"変更 {changed} 件 / スキップ {skipped} 件 / エスカレーション {escalated} 件")
    if escalated:
        print("\n⚠ 原本と食い違う修正指示がありました。")
        print("  該当カードは disputed にし、承認は反映していません。")
        print("  knowledge/escalation.md を確認し、圭一郎さんに出典をご確認ください。")
    if args.apply:
        print("\nカードに書き込みました。次を実行して検証してください:")
        print("  python3 knowledge/verify_cards.py")
    else:
        print("\nドライランです。反映するには --apply を付けて再実行してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
