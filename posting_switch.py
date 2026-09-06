#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""投稿の緊急停止スイッチ。

## なぜ必要か

X と Instagram の自動投稿は launchd で15分ごとに動いている。
これを止める手段が `launchctl` しかなく、コマンドを知らないと止められない。
誤った内容がキューに入ったとき、康二郎さんがその場で止められる必要がある。

スイッチはスプレッドシートの `運用スイッチ` タブに置く。
投稿処理は起動直後にここを読み、`停止` なら1件も投稿せずに終了する。

## 設計の理由

- **既定は「停止」ではなく「稼働」。** ただしシートが読めない・タブが無い等の
  異常時は**停止側に倒す**（fail-safe）。通信が不安定なこの環境では、
  読めなかったときに投稿を続けるほうが危険
- スイッチはセル1つ。プルダウンで `稼働` / `停止` を選ぶだけ
- 誰がいつ切り替えたかを残す（切り替えた人が自分で書く欄）

    /usr/bin/python3 posting_switch.py            # 現在の状態を表示
    /usr/bin/python3 posting_switch.py --setup    # タブを作る
    /usr/bin/python3 posting_switch.py --stop     # 停止にする
    /usr/bin/python3 posting_switch.py --start    # 稼働にする
"""

import argparse
import os
import sys
import time
from datetime import datetime

import gspread

KEY = os.environ.get("SPREADSHEET_KEY", "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")
TAB = "運用スイッチ"
CELL = "B2"          # ここだけを見る
RUNNING = "稼働"
STOPPED = "停止"


def _sheet():
    gc = gspread.service_account(
        filename=os.path.expanduser("~/.config/gspread/service_account.json"))
    return gc.open_by_key(KEY)


def is_posting_enabled(logger=None) -> bool:
    """投稿してよいかを返す。

    **読めなかった場合は False（停止側）を返す。** 投稿は取り消せないため、
    判断できないときは動かさないほうが安全。
    """
    def say(msg):
        if logger:
            logger.warning(msg)
        else:
            print(msg, file=sys.stderr)

    # 一時的な通信エラーで丸ごと見送るのはもったいない。
    # 2026-09-06 に実測したところ、15分おきの実行のうち5%ほどが
    # APIError で読めずに投稿を見送っていた。数回は粘る。
    # ただし粘っても読めなければ、これまでどおり停止側に倒す
    val = None
    last = None
    for attempt in range(3):
        try:
            ws = _sheet().worksheet(TAB)
            val = (ws.acell(CELL).value or "").strip()
            break
        except gspread.WorksheetNotFound:
            say(f"『{TAB}』タブがありません。安全のため投稿を行いません。"
                f"  /usr/bin/python3 posting_switch.py --setup で作成してください")
            return False
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(3 * (2 ** attempt))

    if val is None:
        say(f"投稿スイッチを読めませんでした（{type(last).__name__}、3回試行）。"
            "安全のため投稿を行いません")
        return False

    if val == RUNNING:
        return True
    if val == STOPPED:
        say(f"投稿スイッチが『{STOPPED}』です。投稿を行いません")
        return False
    say(f"投稿スイッチの値が不正です（'{val}'）。安全のため投稿を行いません")
    return False


def setup():
    sh = _sheet()
    try:
        ws = sh.worksheet(TAB)
        print(f"『{TAB}』は既にあります")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=TAB, rows=20, cols=4)
        print(f"『{TAB}』を作成しました")

    ws.update(values=[
        ["", "", "", ""],
        ["投稿スイッチ", RUNNING, "← ここを『停止』にすると、X・Instagram の自動投稿が止まります",
         "最終変更"],
        ["", "", "15分ごとの自動投稿は、動き出す前に必ずこのセルを見ます", ""],
        ["", "", "シートが読めないときも安全のため投稿しません", ""],
        ["", "", "", ""],
        ["切り替えの記録", "", "", ""],
        ["日時", "誰が", "どちらに", "理由"],
    ], range_name="A1")

    sid = ws.id
    sh.batch_update({"requests": [
        {"setDataValidation": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2,
                      "startColumnIndex": 1, "endColumnIndex": 2},
            "rule": {"condition": {"type": "ONE_OF_LIST", "values": [
                {"userEnteredValue": RUNNING}, {"userEnteredValue": STOPPED}]},
                "showCustomUi": True, "strict": True}}},
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2,
                      "startColumnIndex": 1, "endColumnIndex": 2},
            "cell": {"userEnteredFormat": {
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True, "fontSize": 14}}},
            "fields": "userEnteredFormat(horizontalAlignment,textFormat)"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 130}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": 2, "endIndex": 3},
            "properties": {"pixelSize": 480}, "fields": "pixelSize"}},
        {"updateSheetProperties": {
            "properties": {"sheetId": sid, "hidden": False, "index": 0},
            "fields": "hidden,index"}},
    ]})
    print(f"  https://docs.google.com/spreadsheets/d/{KEY}/edit#gid={sid}")
    print(f"  {CELL} セルのプルダウンで『{RUNNING}』『{STOPPED}』を切り替えます")


def switch(to: str, who: str, why: str):
    ws = _sheet().worksheet(TAB)
    before = (ws.acell(CELL).value or "").strip()
    ws.update_acell(CELL, to)
    rows = ws.get_all_values()
    ws.update(values=[[datetime.now().strftime("%Y-%m-%d %H:%M"), who,
                       f"{before} → {to}", why]],
              range_name=f"A{len(rows) + 1}")
    print(f"✅ 投稿スイッチ: {before} → {to}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--who", default="（コマンドから）")
    ap.add_argument("--why", default="")
    a = ap.parse_args()

    if a.setup:
        setup()
    elif a.stop:
        switch(STOPPED, a.who, a.why or "手動で停止")
    elif a.start:
        switch(RUNNING, a.who, a.why or "手動で再開")
    else:
        ok = is_posting_enabled()
        print(f"投稿: {'稼働中' if ok else '停止中'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
