#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""週次記事レビュー用スプレッドシートを作成する。

設計方針:
  - 圭一郎さんが編集するのは「ステータス／修正版／修正種別／修正理由／今後の扱い」の5列だけ
  - 自由入力よりプルダウンを優先（表記ゆれを防ぎ、機械的に集計できるようにする）
  - AI原稿は上書きさせない。修正は別列に書いてもらい、差分を保持する
  - 修正理由を選択式で取ることで、知識層への還元先を機械判定できるようにする

実行: /usr/bin/python3 create_review_sheet.py
      （gspread は /usr/bin/python3 にインストール済み。homebrew python3.14 は pyexpat が壊れている）
"""

import re
import sys
from pathlib import Path

import gspread
from gspread.utils import ValidationConditionType

ROOT = Path(__file__).resolve().parent
EVID = ROOT / "knowledge" / "evidence"

# サービスアカウントは Drive 容量を持たないため新規スプレッドシートを作成できない。
# 圭一郎さんと共有済みの既存シートにタブを追加する（不要になればタブ削除で戻せる）。
SPREADSHEET_KEY = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"

# タブ名は「週次_」で始めて既存タブと区別する
TAB_REVIEW = "週次_レビュー"
TAB_BREAKDOWN = "週次_内訳"
TAB_CARDS = "週次_カード承認"
TAB_CONFIG = "週次_設定"

# --- プルダウンの選択肢 ---------------------------------------------------

STATUS = ["AI下書き", "要確認あり", "圭一郎OK", "要修正", "投稿予約", "投稿済"]

GRADE = [
    "A: 確認済みカードの言い換えのみ",
    "B: 新しい組み合わせ・解釈を含む",
    "C: 新規数値・ニュース・医療的表現を含む",
]

# taxonomy.md と対応。コードだけだと圭一郎さんが選べないので説明文を付ける
FIX_TYPE = [
    "E1 実験条件の誤り（時間/回数/期間/対象）",
    "E2 出典・所属の誤り",
    "E3 数値の誤り",
    "E4 結果の誤読・過大解釈",
    "F1 イベント情報の誤り（期数/日時/費用/会場）",
    "F2 告知しない",
    "X1 効果の断言",
    "X2 過度な強調",
    "X3 医療行為との混同",
    "B1 ブランド表記",
    "B2 トーン指定",
    "S1 構成・読みやすさ",
    "T1 誤字脱字",
]

APPLY = [
    "恒久ルールにする",
    "今回限り",
    "不要",
]

# --- シート定義 -----------------------------------------------------------

REVIEW_HEADER = [
    "記事ID", "週", "媒体", "投稿予定日", "分級", "使用カードID",
    "AI原稿", "ステータス",
    "修正版（ここに直接お書きください）", "修正種別", "修正理由", "今後の扱い",
    "承認稿", "更新日時",
]

# 圭一郎さんが編集する列（1始まり）: H=8, I=9, J=10, K=11, L=12
EDITABLE_COLS = (8, 9, 10, 11, 12)

BREAKDOWN_HEADER = [
    "記事ID", "カード由来の文", "AIの解釈・つなぎ", "CTA", "使った時事文脈",
    "外部情報（季節・生活）", "外部情報（要確認）", "[要確認]タグ", "ChatGPTの指摘（改稿前）",
]

# カード承認タブ。圭一郎さんが判断するのに必要な材料を左に、承認欄を右に置く
CARD_HEADER = [
    "カードID", "タイトル", "出典", "対象(n)", "介入",
    "原文（全文）", "主な結果", "この結果から言ってはいけないこと",
    "解釈の承認", "公開の承認", "コメント（直すべき点）", "承認者", "承認日",
    "転記(自動)", "状態(自動)",
]

# 圭一郎さんが編集する列（1始まり）: I〜M
CARD_EDITABLE = (9, 10, 11, 12, 13)

# 承認プルダウン。「済/未」ではなく行為として書く（シニア配慮）
APPROVE = [
    "承認する",
    "要修正（コメント欄に記入）",
    "保留・判断できない",
]


def read_front_matter(path: Path) -> dict:
    """カードのYAMLフロントマターから必要なフィールドだけ拾う。

    PyYAMLに依存せず、必要なキーを正規表現で取る（複数行ブロックは1行目のみ）。
    """
    text = path.read_text(encoding="utf-8")
    fm = text.split("---", 2)[1] if text.startswith("---") else text

    def scalar(key: str) -> str:
        m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
        if not m:
            return ""
        v = m.group(1).strip()
        # `status: disputed  # 理由` のようなインラインコメントを落とす
        v = re.sub(r"\s+#.*$", "", v).strip()
        return "" if v in ("|", ">", "null") else v

    def approval(key: str) -> str:
        m = re.search(rf"^approval:.*?^\s+{key}:\s*(\S+)", fm, re.M | re.S)
        return m.group(1) if m else "?"

    def multiline(key: str, limit: int = 0) -> str:
        """`key: |` ブロックを本文として取り出す。limit>0 なら先頭N行に絞る。"""
        m = re.search(rf"^{key}:\s*\|\s*$(.*?)^\w[\w_]*:", fm, re.S | re.M)
        if not m:
            return ""
        lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
        if limit:
            lines = lines[:limit]
        return "\n".join(lines)

    def findings_summary() -> str:
        """findings を「指標: 結果」の箇条書きにする。

        有意差がなかった項目には ⚠ を付けて目立たせる。ここを見落とすと過大解釈になるため。
        """
        blk = re.search(r"^findings:\s*$(.*?)^\w[\w_]*:", fm, re.S | re.M)
        if not blk:
            return ""
        out = []
        for item in re.split(r"^\s*-\s+metric:", blk.group(1), flags=re.M)[1:]:
            metric = item.splitlines()[0].strip()
            res = re.search(r"^\s*result:\s*(.+)$", item, re.M)
            sig = re.search(r"^\s*significant:\s*(\S+)\s*$", item, re.M)
            mark = "⚠ " if sig and sig.group(1) == "false" else ""
            out.append(f"{mark}{metric}: {res.group(1).strip() if res else '—'}")
        return "\n".join(out)

    src = scalar("source_file").split("/")[-1]
    venue = scalar("venue")

    return {
        "id": scalar("id"),
        "title": scalar("title"),
        "source": f"{venue}\n（{src}）" if venue else src,
        "subjects": scalar("subjects"),
        "n": scalar("n"),
        "intervention": scalar("intervention"),
        # 承認判断には原文全体が要る。抜粋にすると「原文が切れていて確認不可」となり
        # レビューが止まる（2026-07-29 のテストで実際に発生した）
        "verbatim": multiline("verbatim"),
        "findings": findings_summary(),
        "transcription": approval("transcription"),
        "status": scalar("status"),
        "ng": multiline("generalization_ng"),
    }


def dropdown(sheet_id: int, col: int, values: list, rows: int = 500) -> dict:
    """1列まるごとにプルダウンを設定するリクエストを組み立てる。"""
    return {
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,          # ヘッダー行を除く
                "endRowIndex": rows,
                "startColumnIndex": col - 1,
                "endColumnIndex": col,
            },
            "rule": {
                "condition": {
                    "type": ValidationConditionType.one_of_list.value,
                    "values": [{"userEnteredValue": v} for v in values],
                },
                "showCustomUi": True,
                "strict": False,   # 想定外の値も一応入力できるようにする
            },
        }
    }


SHOW_TABS = False   # --show で True になる


def main() -> int:
    global SHOW_TABS
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true",
                    help="タブを表示状態にする（圭一郎さんに共有する準備が整ってから）")
    SHOW_TABS = ap.parse_args().show

    if not EVID.is_dir():
        print(f"カードディレクトリが見つかりません: {EVID}")
        return 1

    gc = gspread.service_account()
    sh = gc.open_by_key(SPREADSHEET_KEY)
    print(f"対象: {sh.title}")
    print(f"URL : https://docs.google.com/spreadsheets/d/{sh.id}")

    def tab(title: str, rows: int, cols: int):
        """タブを作る。既にあれば中身を消して作り直す（冪等にする）。"""
        try:
            ws = sh.worksheet(title)
            ws.clear()
            ws.resize(rows=rows, cols=cols)
            print(f"  既存タブを初期化: {title}")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=rows, cols=cols)
            print(f"  タブを作成: {title}")
        return ws

    # --- レビュー ---------------------------------------------------------
    review = tab(TAB_REVIEW, 500, len(REVIEW_HEADER))
    review.update(values=[REVIEW_HEADER], range_name="A1")
    review.freeze(rows=1)

    # --- 内訳 -------------------------------------------------------------
    bd = tab(TAB_BREAKDOWN, 500, len(BREAKDOWN_HEADER))
    bd.update(values=[BREAKDOWN_HEADER], range_name="A1")
    bd.freeze(rows=1)

    # --- カード一覧（knowledge/evidence から生成） -------------------------
    cards = [read_front_matter(p) for p in sorted(EVID.glob("EV-*.md"))]
    card_rows = [
        [
            c["id"], c["title"], c["source"],
            f'{c["subjects"]}（n={c["n"] or "不明"}）',
            c["intervention"], c["verbatim"], c["findings"], c["ng"],
            "", "", "", "", "",          # I〜M: 承認欄（圭一郎さんが記入）
            c["transcription"], c["status"],
        ]
        for c in cards
    ]
    cw = tab(TAB_CARDS, max(len(card_rows) + 20, 60), len(CARD_HEADER))
    cw.update(values=[CARD_HEADER] + card_rows, range_name="A1")
    cw.freeze(rows=1)
    print(f"カード一覧に {len(card_rows)} 枚を書き出しました")

    # --- 設定（プルダウンの元データを人が確認できるように残す） -----------
    cfg = tab(TAB_CONFIG, 40, 4)
    longest = max(len(STATUS), len(GRADE), len(FIX_TYPE), len(APPLY))
    cfg_rows = [["ステータス", "分級", "修正種別", "今後の扱い"]]
    for i in range(longest):
        cfg_rows.append([
            STATUS[i] if i < len(STATUS) else "",
            GRADE[i] if i < len(GRADE) else "",
            FIX_TYPE[i] if i < len(FIX_TYPE) else "",
            APPLY[i] if i < len(APPLY) else "",
        ])
    cfg.update(values=cfg_rows, range_name="A1")

    # --- プルダウン・書式 -------------------------------------------------
    rid = review.id
    requests = [
        dropdown(rid, 5, GRADE),      # E 分級
        dropdown(rid, 8, STATUS),     # H ステータス
        dropdown(rid, 10, FIX_TYPE),  # J 修正種別
        dropdown(rid, 12, APPLY),     # L 今後の扱い
        # ヘッダーを太字＋折り返し
        {
            "repeatCell": {
                "range": {"sheetId": rid, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "wrapStrategy": "WRAP",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat(textFormat,wrapStrategy,verticalAlignment)",
            }
        },
        # 圭一郎さんが書く列を薄い黄色にして「ここに書く」と分かるようにする
        {
            "repeatCell": {
                "range": {
                    "sheetId": rid,
                    "startRowIndex": 0,
                    "startColumnIndex": min(EDITABLE_COLS) - 1,
                    "endColumnIndex": max(EDITABLE_COLS),
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 1.0, "green": 0.98, "blue": 0.82}
                    }
                },
                "fields": "userEnteredFormat.backgroundColor",
            }
        },
        # AI原稿列は折り返して読みやすく＋幅を広げる
        {
            "repeatCell": {
                "range": {"sheetId": rid, "startColumnIndex": 6, "endColumnIndex": 7},
                "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                "fields": "userEnteredFormat.wrapStrategy",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": rid, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7},
                "properties": {"pixelSize": 420},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {"sheetId": rid, "dimension": "COLUMNS", "startIndex": 8, "endIndex": 9},
                "properties": {"pixelSize": 420},
                "fields": "pixelSize",
            }
        },
    ]

    # --- カード承認タブの書式 ---------------------------------------------
    cid = cw.id
    n_rows = len(card_rows) + 1
    requests += [
        dropdown(cid, 9, APPROVE, rows=n_rows),    # I 解釈の承認
        dropdown(cid, 10, APPROVE, rows=n_rows),   # J 公開の承認
        {
            "repeatCell": {
                "range": {"sheetId": cid, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "wrapStrategy": "WRAP",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat(textFormat,wrapStrategy,verticalAlignment)",
            }
        },
        # 全セル折り返し＋上揃え（原文抜粋が長いため）
        {
            "repeatCell": {
                "range": {"sheetId": cid, "startRowIndex": 1, "endRowIndex": n_rows},
                "cell": {
                    "userEnteredFormat": {
                        "wrapStrategy": "WRAP",
                        "verticalAlignment": "TOP",
                    }
                },
                "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
            }
        },
        # 承認欄を黄色にして「ここに記入」と分かるようにする
        {
            "repeatCell": {
                "range": {
                    "sheetId": cid,
                    "startRowIndex": 0,
                    "endRowIndex": n_rows,
                    "startColumnIndex": min(CARD_EDITABLE) - 1,
                    "endColumnIndex": max(CARD_EDITABLE),
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 1.0, "green": 0.98, "blue": 0.82}
                    }
                },
                "fields": "userEnteredFormat.backgroundColor",
            }
        },
        # disputed のカードは行全体を薄い赤にして使用禁止を示す
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": cid, "startRowIndex": 1, "endRowIndex": n_rows}],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": '=$O2="disputed"'}],
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 0.87, "blue": 0.87}
                        },
                    },
                },
                "index": 0,
            }
        },
    ]
    # 列幅（原文抜粋・結果・NG は広く、承認欄は選びやすい幅に）
    for start, end, px in [(1, 2, 220), (2, 3, 170), (4, 5, 200),
                           (5, 6, 560), (6, 7, 280), (7, 8, 320),
                           (8, 10, 150), (10, 11, 240)]:
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": cid, "dimension": "COLUMNS",
                          "startIndex": start, "endIndex": end},
                "properties": {"pixelSize": px},
                "fields": "pixelSize",
            }
        })

    # 圭一郎さんにはまだこのシステムを説明していないため、タブは非表示にしておく。
    # 準備が整ったら --show を付けて実行すると表示に切り替わる。
    for ws in (review, bd, cw, cfg):
        requests.append({"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "hidden": not SHOW_TABS},
            "fields": "hidden",
        }})

    sh.batch_update({"requests": requests})
    print("プルダウン・書式を設定しました")
    if SHOW_TABS:
        print("タブを表示状態にしました（圭一郎さんから見えます）")
    else:
        print("タブは非表示です。表示するには --show を付けて再実行してください")
    print(f"\n承認はここで行えます:")
    print(f"  https://docs.google.com/spreadsheets/d/{sh.id}/edit#gid={cid}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
