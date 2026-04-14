#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
イベント投稿シートに「投稿キュー貼付用」列を追加。
列を選択 → Cmd+Shift+V（値貼付）で投稿キューに行ごと貼れるようにする。

IGイベント投稿: Q-Z列 (10列) → IG投稿キュー A-J列に対応
Xイベント投稿: O-Y列 (11列) → X投稿キュー A-K列に対応
"""

import gspread

SPREADSHEET_ID = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"

gc = gspread.service_account()
sh = gc.open_by_key(SPREADSHEET_ID)


def add_columns_if_needed(ws, target_count):
    """シートの列数がtarget_count未満なら追加"""
    current = ws.col_count
    if current < target_count:
        ws.add_cols(target_count - current)
        print(f"  列追加: {current} → {target_count}")


def col_letter(idx_1based):
    """1-based column index to letter (A, B, ..., Z, AA, ...)"""
    s = ''
    n = idx_1based
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# ============================================================
# IGイベント投稿 → IG投稿キュー
# ============================================================
print("=== IGイベント投稿 ===")
ig_ws = sh.worksheet("IGイベント投稿")
ig_data = ig_ws.get_all_values()
last_row = len(ig_data)
print(f"  既存行数: {last_row}")

# Q列(17)〜Z列(26) を確保
add_columns_if_needed(ig_ws, 26)

# ヘッダー (Q1:Z1)
ig_queue_header = [
    '【貼付】投稿日時', 'キャプション',
    '画像1', '画像リンク1',
    '画像2', '画像リンク2',
    '画像3', '画像リンク3',
    'ステータス', 'メモ',
]
ig_ws.update(values=[ig_queue_header], range_name='Q1:Z1', value_input_option='USER_ENTERED')

# データ行 (Q2:Z<last>) を式で埋める
# IGイベント投稿 列マップ:
#   G=キャプション, J=画像リンク, L=投稿予定日
ig_formulas = []
for row_idx in range(2, last_row + 1):
    # 空行はスキップ
    no = ig_data[row_idx - 1][0].strip() if len(ig_data[row_idx - 1]) > 0 else ''
    if not no:
        ig_formulas.append([''] * 10)
        continue
    ig_formulas.append([
        f'=L{row_idx}',          # 投稿日時 ← 投稿予定日
        f'=G{row_idx}',          # キャプション
        '',                       # 画像1ラベル
        f'=J{row_idx}',          # 画像リンク1
        '',                       # 画像2
        '',                       # 画像リンク2
        '',                       # 画像3
        '',                       # 画像リンク3
        '予約',                    # ステータス
        '',                       # メモ
    ])

ig_ws.update(
    values=ig_formulas,
    range_name=f'Q2:Z{last_row}',
    value_input_option='USER_ENTERED',
)
print(f"  Q-Z列に {len(ig_formulas)} 行分の貼付用式を設定")

# ヘッダーとデータ範囲に背景色（薄い黄色）
ig_sid = ig_ws.id
ig_format_requests = [{
    'repeatCell': {
        'range': {
            'sheetId': ig_sid,
            'startRowIndex': 0, 'endRowIndex': last_row,
            'startColumnIndex': 16, 'endColumnIndex': 26,
        },
        'cell': {
            'userEnteredFormat': {
                'backgroundColor': {'red': 1.0, 'green': 0.98, 'blue': 0.85},
            }
        },
        'fields': 'userEnteredFormat.backgroundColor',
    }
}, {
    # ヘッダー行は太字
    'repeatCell': {
        'range': {
            'sheetId': ig_sid,
            'startRowIndex': 0, 'endRowIndex': 1,
            'startColumnIndex': 16, 'endColumnIndex': 26,
        },
        'cell': {
            'userEnteredFormat': {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 1.0, 'green': 0.92, 'blue': 0.6},
            }
        },
        'fields': 'userEnteredFormat.textFormat,userEnteredFormat.backgroundColor',
    }
}]
sh.batch_update({'requests': ig_format_requests})

print()

# ============================================================
# Xイベント投稿 → X投稿キュー
# ============================================================
print("=== Xイベント投稿 ===")
x_ws = sh.worksheet("Xイベント投稿")
x_data = x_ws.get_all_values()
x_last_row = len(x_data)
print(f"  既存行数: {x_last_row}")

# O(15)〜Y(25) = 11列確保
add_columns_if_needed(x_ws, 25)

# ヘッダー (O1:Y1)
x_queue_header = [
    '【貼付】投稿日時', '投稿テキスト',
    '画像1', '画像リンク1',
    '画像2', '画像リンク2',
    '画像3', '画像リンク3',
    'ステータス', 'メモ', 'リプライテキスト',
]
x_ws.update(values=[x_queue_header], range_name='O1:Y1', value_input_option='USER_ENTERED')

# Xイベント投稿 列マップ:
#   F=投稿テキスト, I=画像リンク, K=投稿予定日
x_formulas = []
for row_idx in range(2, x_last_row + 1):
    name = x_data[row_idx - 1][0].strip() if len(x_data[row_idx - 1]) > 0 else ''
    if not name:
        x_formulas.append([''] * 11)
        continue
    x_formulas.append([
        f'=K{row_idx}',          # 投稿日時 ← 投稿予定日
        f'=F{row_idx}',          # 投稿テキスト
        '',                       # 画像1
        f'=I{row_idx}',          # 画像リンク1
        '',                       # 画像2
        '',                       # 画像リンク2
        '',                       # 画像3
        '',                       # 画像リンク3
        '予約',                    # ステータス
        '',                       # メモ
        '',                       # リプライテキスト
    ])

x_ws.update(
    values=x_formulas,
    range_name=f'O2:Y{x_last_row}',
    value_input_option='USER_ENTERED',
)
print(f"  O-Y列に {len(x_formulas)} 行分の貼付用式を設定")

# 背景色
x_sid = x_ws.id
x_format_requests = [{
    'repeatCell': {
        'range': {
            'sheetId': x_sid,
            'startRowIndex': 0, 'endRowIndex': x_last_row,
            'startColumnIndex': 14, 'endColumnIndex': 25,
        },
        'cell': {
            'userEnteredFormat': {
                'backgroundColor': {'red': 1.0, 'green': 0.98, 'blue': 0.85},
            }
        },
        'fields': 'userEnteredFormat.backgroundColor',
    }
}, {
    'repeatCell': {
        'range': {
            'sheetId': x_sid,
            'startRowIndex': 0, 'endRowIndex': 1,
            'startColumnIndex': 14, 'endColumnIndex': 25,
        },
        'cell': {
            'userEnteredFormat': {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 1.0, 'green': 0.92, 'blue': 0.6},
            }
        },
        'fields': 'userEnteredFormat.textFormat,userEnteredFormat.backgroundColor',
    }
}]
sh.batch_update({'requests': x_format_requests})

print("\n完了!")
print()
print("=== 使い方 ===")
print("1. IGイベント投稿シートで貼付したい行の Q列〜Z列 を選択")
print("   (例: 仙台スターライトNo.2 → Q3:Z3)")
print("2. Cmd+C でコピー")
print("3. IG投稿キューシートの空き行 A列にカーソル")
print("4. Cmd+Shift+V で「値のみ貼り付け」")
print("5. A列の投稿日時を希望の日時に編集 (例: 2026/04/10 19:00)")
print()
print("Xも同様: O列〜Y列を選択して X投稿キューに貼付")
