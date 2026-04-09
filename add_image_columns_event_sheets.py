#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Xイベント投稿・IGイベント投稿シートに画像リンク列と画像表示列を追加"""

import gspread
from google.oauth2.service_account import Credentials
import os

SPREADSHEET_ID = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"

gc = gspread.service_account()
sh = gc.open_by_key(SPREADSHEET_ID)


def add_image_columns(ws, insert_after_col_idx, header_bg_color):
    """
    シートに「画像リンク」「画像表示」列を挿入する。

    Args:
        ws: gspread worksheet
        insert_after_col_idx: 挿入位置（0-indexed）。この列の後に2列追加
        header_bg_color: ヘッダー背景色 dict
    """
    sheet_id = ws.id
    num_rows = ws.row_count

    # 1. 列を2つ挿入
    sh.batch_update({'requests': [
        {
            'insertDimension': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': insert_after_col_idx + 1,
                    'endIndex': insert_after_col_idx + 3,
                },
                'inheritFromBefore': False,
            }
        }
    ]})
    print(f"  列{insert_after_col_idx + 2}〜{insert_after_col_idx + 3}に2列挿入")

    # 列番号（1-indexed for gspread）
    link_col = insert_after_col_idx + 2  # 1-indexed
    image_col = insert_after_col_idx + 3

    # A1表記用
    def col_letter(n):
        s = ''
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    link_letter = col_letter(link_col)
    image_letter = col_letter(image_col)

    # 2. ヘッダー設定
    ws.update(f'{link_letter}1:{image_letter}1',
              [['画像リンク', '画像表示']],
              value_input_option='USER_ENTERED')
    print(f"  ヘッダー設定: {link_letter}1=画像リンク, {image_letter}1=画像表示")

    # 3. 画像表示列にIMAGE関数を設定（2行目〜データ末尾）
    all_data = ws.get_all_values()
    data_rows = len(all_data)
    if data_rows > 1:
        formulas = []
        for row in range(2, data_rows + 1):
            formula = f'=IF({link_letter}{row}<>"", IMAGE({link_letter}{row}), "")'
            formulas.append([formula])
        ws.update(f'{image_letter}2:{image_letter}{data_rows}',
                  formulas,
                  value_input_option='USER_ENTERED')
        print(f"  IMAGE関数設定: {image_letter}2〜{image_letter}{data_rows}")

    # 4. フォーマット設定
    requests = []

    # ヘッダーの色
    requests.append({
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': 0, 'endRowIndex': 1,
                'startColumnIndex': insert_after_col_idx + 1,
                'endColumnIndex': insert_after_col_idx + 3,
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': header_bg_color,
                    'textFormat': {
                        'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                        'bold': True,
                    },
                }
            },
            'fields': 'userEnteredFormat.backgroundColor,userEnteredFormat.textFormat',
        }
    })

    # 列幅: 画像リンク=200px, 画像表示=150px
    for offset, width in [(1, 200), (2, 150)]:
        col_idx = insert_after_col_idx + offset
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': col_idx,
                    'endIndex': col_idx + 1,
                },
                'properties': {'pixelSize': width},
                'fields': 'pixelSize',
            }
        })

    # 行の高さ（画像表示用に80px）
    if data_rows > 1:
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'ROWS',
                    'startIndex': 1,
                    'endIndex': data_rows,
                },
                'properties': {'pixelSize': 80},
                'fields': 'pixelSize',
            }
        })

    sh.batch_update({'requests': requests})
    print(f"  フォーマット適用完了")


# ============================================================
# 1. Xイベント投稿
# ============================================================
print("=== Xイベント投稿 ===")
x_ws = sh.worksheet("Xイベント投稿")
# 現在の列: A:イベント名 B:カテゴリ C:開催日 D:開催場所 E:投稿タイプ
#           F:投稿テキスト G:Xカウント H:メディア I:投稿予定日 ...
# H(メディア)の後 = index 7 の後に挿入
x_header_bg = {'red': 0.05, 'green': 0.15, 'blue': 0.55}
add_image_columns(x_ws, insert_after_col_idx=7, header_bg_color=x_header_bg)
print()

# ============================================================
# 2. IGイベント投稿
# ============================================================
print("=== IGイベント投稿 ===")
ig_ws = sh.worksheet("IGイベント投稿")
# 現在の列: A:No B:イベント名 C:カテゴリ D:開催日 E:開催場所 F:投稿タイプ
#           G:キャプション H:形式 I:画像メモ J:投稿予定日 ...
# I(画像メモ)の後 = index 8 の後に挿入
ig_header_bg = {'red': 0.95, 'green': 0.45, 'blue': 0.15}
add_image_columns(ig_ws, insert_after_col_idx=8, header_bg_color=ig_header_bg)

print("\n完了!")
print("使い方: 「画像リンク」列にDrive画像URLを貼ると「画像表示」列に自動表示されます")
print("  例: https://drive.google.com/uc?export=view&id=ファイルID")
