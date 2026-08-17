#!/usr/bin/env python3
"""圭一郎さんがOKした投稿から、Approved claim（AC）カードを切り出す。

## なぜこの方式にしたか

これまでは Evidence カード12枚に「解釈承認・公開承認」を求めていた。0/12 のまま
数週間動かなかった。3者の壁打ちで、いずれもこの設計に反対だった。

> EVカードのレビューは科学論文の読解作業であり、本人が3〜7月に実証した行動
> （投稿文の校正）とは別のスキル・別の心理的負荷。（Fable 5）

> 現時点で大規模な承認制度を載せると、在庫問題を承認問題に変えてしまいます。（ChatGPT）

そこで承認の対象を**カードから完成投稿に移す**。圭一郎さんは「この文でよいか」だけを
見ればよく、これは3〜7月に実際にやっていた作業と同じである。

OKが出た投稿から、カード由来の言い回しを AC として切り出す。以後、同じ言い回しを
使う投稿は A 分級になり、確認が軽くなる。**ACライブラリが過去のOKから機械的に育ち、
レビュー負荷が減っていく**のが狙い。

    /usr/bin/python3 extract_ac.py            # 何ができるか見る
    /usr/bin/python3 extract_ac.py --apply    # 実際にカードを作る
"""

import argparse
import os
import re
from datetime import date
from pathlib import Path

import gspread

ROOT = Path(__file__).resolve().parent
CLAIMS = ROOT / "knowledge" / "claims"
KEY = os.environ.get("SPREADSHEET_KEY", "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")

# このステータスになった記事だけを「承認済み」とみなす。
#
# 当初 "投稿予約" "投稿済" も含めていたが、Fable 5 の指摘で外した。
# それらは康二郎さんが運用上つけられるステータスであり、
# **圭一郎さんが一度も見ていない投稿から AC が作られうる**。
# AC の存在意義は「本人のOKの結晶」であることなので、ここが緩いと方式全体が崩れる。
APPROVED = ("圭一郎OK",)

# 1文が短すぎるものは主張として切り出さない
MIN_LEN = 18


def next_id() -> int:
    CLAIMS.mkdir(parents=True, exist_ok=True)
    ns = [int(m.group(1)) for p in CLAIMS.glob("AC-*.md")
          for m in [re.match(r"AC-(\d+)", p.name)] if m]
    return max(ns) + 1 if ns else 1


def existing_claims() -> dict:
    """既存の AC を claim_text で引けるようにする。同じ言い回しを二重に作らない。"""
    out = {}
    for p in sorted(CLAIMS.glob("AC-*.md")):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^claim_text:\s*(.*)$", t, re.M)
        if m:
            out[norm(m.group(1))] = p.stem
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).strip("　 「」『』")


def sentences(block: str) -> list:
    """カード由来の文を、主張の単位に割る。"""
    out = []
    for chunk in re.split(r"[\n]+", block):
        chunk = re.sub(r"^\s*[-・*]\s*", "", chunk).strip()
        for s in re.split(r"(?<=。)", chunk):
            s = s.strip()
            if len(s) >= MIN_LEN:
                out.append(s)
    return out


def load_rows(gc):
    """承認済みの記事と、その内訳（カード由来の文）を突き合わせる。"""
    sh = gc.open_by_key(KEY)
    rv = sh.worksheet("週次_レビュー").get_all_values()
    bd = sh.worksheet("週次_内訳").get_all_values()
    if not rv or not bd:
        return []

    rh, bh = rv[0], bd[0]
    i_id, i_st = rh.index("記事ID"), rh.index("ステータス")
    i_cards, i_media = rh.index("使用カードID"), rh.index("媒体")
    i_fixed = rh.index("承認稿") if "承認稿" in rh else None
    i_edit = rh.index("修正版（ここに直接お書きください）") if "修正版（ここに直接お書きください）" in rh else None

    b_id, b_src = bh.index("記事ID"), bh.index("カード由来の文")
    breakdown = {r[b_id]: r[b_src] for r in bd[1:] if len(r) > b_src and r[b_id]}

    out = []
    for r in rv[1:]:
        if len(r) <= i_st or r[i_st].strip() not in APPROVED:
            continue
        aid = r[i_id].strip()
        if not aid or aid.startswith("TEST-"):
            continue          # 検証用の生成物は承認の証拠にしない
        # 圭一郎さんが書き直した文があるなら、そちらが承認された言い回し
        approved_text = ""
        for i in (i_fixed, i_edit):
            if i is not None and len(r) > i and r[i].strip():
                approved_text = r[i].strip()
                break
        out.append({
            "id": aid,
            "media": r[i_media].strip(),
            "cards": [c.strip() for c in r[i_cards].split(",") if c.strip()],
            "source_sentences": sentences(breakdown.get(aid, "")),
            "rewritten": approved_text,
        })
    return out


def claim_candidates(row: dict) -> list:
    """AC にしてよい文だけを取り出す。

    当初は修正版の全文を文単位で切り出していたが、それだと季節の挨拶や
    つなぎの文まで AC になった（Fable 5 の指摘）。AC は**カード由来の主張**に
    限るべきなので、候補はあくまで `カード由来の文` から取る。

    圭一郎さんが書き直している場合は、対応する文を修正版から探して
    そちらの言い回しを採る。承認されたのは本人が書いた表現のほうだから。
    """
    from difflib import SequenceMatcher

    base = row["source_sentences"]
    if not row["rewritten"]:
        return base

    rewritten = sentences(row["rewritten"])
    out = []
    for s in base:
        best, score = s, 0.0
        for t in rewritten:
            r = SequenceMatcher(None, norm(s), norm(t)).ratio()
            if r > score:
                best, score = t, r
        # 十分似た文があれば書き直し後を採る。似た文が無いなら、
        # 圭一郎さんがその主張を削ったということなので AC にしない。
        if score >= 0.55:
            out.append(best)
    return out


def write_card(n: int, claim: str, based_on: list, media: str, article_id: str) -> Path:
    body = f"""---
id: AC-{n:04d}
based_on: [{', '.join(based_on)}]
claim_text: {claim}
forbidden_variants: []        # 断定形に崩した言い回しが見つかったら追記する
required_qualifier: 承認された言い回しのまま使う。語尾を断定形に変えない
media: [{media}]
approval:
  interpretation: 済
  publication: 済
approved_at: {date.today().isoformat()}
reviewer: 喜田圭一郎
source_article: {article_id}
status: active
---

## 承認の経緯

記事 `{article_id}` に含まれていた主張。圭一郎さんが投稿としてOKを出した時点で、
この言い回しは発信可能と確定した。

カード単位の事前承認ではなく、**完成した投稿への承認から切り出している**。
そのため `based_on` の Evidence カードは未承認のことがあるが、
「この文で出してよい」という判断は取れている。

## 使い方

同じ趣旨を書くときは、この言い回しをそのまま使う。
語尾を「〜します」「〜されます」のような断定形に変えないこと。
"""
    p = CLAIMS / f"AC-{n:04d}.md"
    p.write_text(body, encoding="utf-8")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="実際にカードを作る")
    args = ap.parse_args()

    gc = gspread.service_account(
        filename=os.path.expanduser("~/.config/gspread/service_account.json"))
    rows = load_rows(gc)
    known = existing_claims()

    print(f"承認済み（{'/'.join(APPROVED)}）の記事: {len(rows)}件")
    if not rows:
        print("\nまだありません。週次_レビュー のステータスを『圭一郎OK』にすると、")
        print("その記事に含まれる主張が AC カードになります。")
        return 0

    n = next_id()
    made = skipped = 0
    for r in rows:
        cands = claim_candidates(r)
        for s in cands:
            if norm(s) in known:
                skipped += 1
                continue
            print(f"  + AC-{n:04d}  [{r['media']}] {s[:62]}")
            if args.apply:
                write_card(n, s, r["cards"] or ["(なし)"], r["media"], r["id"])
                known[norm(s)] = f"AC-{n:04d}"
            n += 1
            made += 1

    print(f"\n新規 {made}件 / 既存と重複 {skipped}件")
    if not args.apply:
        print("※ --apply を付けると実際に作成します")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
