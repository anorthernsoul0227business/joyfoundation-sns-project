#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3件の修正を一括実行:
1. 仙台スターライト 19:40統一
2. 延期・告知不要の行をグレーアウト+補足
3. 月別イベント一覧投稿を作成
"""

import gspread
import unicodedata

SPREADSHEET_ID = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"

def x_count(text):
    count = 0
    for c in text:
        if c == '\n': count += 1
        elif unicodedata.east_asian_width(c) in ('F', 'W'): count += 2
        else: count += 1
    return count

gc = gspread.service_account()
sh = gc.open_by_key(SPREADSHEET_ID)

# ============================================================
# 1. 仙台スターライト 19:40確認
# ============================================================
print("=== 1. 仙台スターライト 19:40確認 ===")

# IG
ig_ws = sh.worksheet("IGイベント投稿")
ig_data = ig_ws.get_all_values()

for i, row in enumerate(ig_data[1:], 2):
    event = row[1] if len(row) > 1 else ''
    if '仙台' in event and 'スターライト' in event:
        caption = row[6] if len(row) > 6 else ''
        if '19:30' in caption:
            new_caption = caption.replace('19:30', '19:40')
            ig_ws.update(values=[[new_caption]], range_name=f'G{i}', value_input_option='USER_ENTERED')
            print(f"  IG Row {i}: 19:30→19:40 修正")
        elif '19:40' in caption:
            print(f"  IG Row {i}: 既に19:40 OK")
        else:
            print(f"  IG Row {i}: 時間記載なし")

# X
x_ws = sh.worksheet("Xイベント投稿")
x_data = x_ws.get_all_values()

for i, row in enumerate(x_data[1:], 2):
    event = row[0] if len(row) > 0 else ''
    if '仙台' in event and 'スターライト' in event:
        text = row[5] if len(row) > 5 else ''
        if '19:30' in text:
            new_text = text.replace('19:30', '19:40')
            x_ws.update(values=[[new_text]], range_name=f'F{i}', value_input_option='USER_ENTERED')
            x_ws.update(values=[[f'{x_count(new_text)}/280']], range_name=f'G{i}', value_input_option='USER_ENTERED')
            print(f"  X Row {i}: 19:30→19:40 修正")
        elif '19:40' in text:
            print(f"  X Row {i}: 既に19:40 OK")

# X投稿v2シートも確認（存在する場合のみ）
try:
    x2_ws = sh.worksheet("X投稿v2")
    x2_data = x2_ws.get_all_values()
    for i, row in enumerate(x2_data[1:], 2):
        day = row[0] if len(row) > 0 else ''
        if '仙台' in day:
            text = row[2] if len(row) > 2 else ''
            if '19:30' in text:
                new_text = text.replace('19:30', '19:40')
                x2_ws.update(values=[[new_text]], range_name=f'C{i}', value_input_option='USER_ENTERED')
                print(f"  X投稿v2 Row {i}: 19:30→19:40 修正")
            elif '19:40' in text:
                print(f"  X投稿v2 Row {i}: 既に19:40 OK")
except gspread.exceptions.WorksheetNotFound:
    print("  X投稿v2シートなし（スキップ）")

print()

# ============================================================
# 2. 延期・告知不要の行をグレーアウト
# ============================================================
print("=== 2. 延期・告知不要の行をグレーアウト ===")

ig_sid = ig_ws.id
ig_cols = len(ig_data[0])

# IGの対象行: No.4(row5)=延期, No.13(row14)=告知不要, No.14(row15)=告知不要
grey_rows_ig = {
    5: '⏸️ 4月延期 → 5月(No.12)からスタート',
    14: '🚫 告知不要（内部研修のため）',
    15: '🚫 告知不要（内部研修のため）',
}

grey_bg = {'red': 0.85, 'green': 0.85, 'blue': 0.85}
grey_text = {'red': 0.5, 'green': 0.5, 'blue': 0.5}

ig_requests = []
for row_num, note in grey_rows_ig.items():
    row_idx = row_num - 1  # 0-indexed
    # 行全体をグレー背景+グレー文字
    ig_requests.append({
        'repeatCell': {
            'range': {
                'sheetId': ig_sid,
                'startRowIndex': row_idx, 'endRowIndex': row_idx + 1,
                'startColumnIndex': 0, 'endColumnIndex': ig_cols,
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': grey_bg,
                    'textFormat': {'foregroundColor': grey_text},
                }
            },
            'fields': 'userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor',
        }
    })
    print(f"  IG Row {row_num}: グレーアウト + 補足「{note}」")

sh.batch_update({'requests': ig_requests})

# 補足テキストをメモ列に追加
ig_updates = []
for row_num, note in grey_rows_ig.items():
    # P列(圭一郎さん確認メモ)に補足追加
    ig_updates.append({'range': f'P{row_num}', 'values': [[note]]})

ig_ws.batch_update(ig_updates, value_input_option='USER_ENTERED')
print()

# ============================================================
# 3. 月別イベント一覧投稿を作成
# ============================================================
print("=== 3. 月別イベント一覧投稿を作成 ===")

# 有効なイベント（延期・告知不要以外）を月別に分類
skip_nos = {4, 13, 14}
events_by_month = {}

# ヘッダーから列インデックスを取得
ig_header = ig_data[0]
ci = {h: i for i, h in enumerate(ig_header)}

for row in ig_data[1:]:
    no = row[ci['No']].strip() if ci['No'] < len(row) else ''
    if not no or not no.isdigit():
        continue
    no_int = int(no)
    if no_int in skip_nos:
        continue

    event_name = row[ci['イベント名']] if ci['イベント名'] < len(row) else ''
    date_str = row[ci['開催日']] if ci['開催日'] < len(row) else ''
    place = row[ci['開催場所']] if ci['開催場所'] < len(row) else ''

    # 月を判定
    month = None
    for m in [4, 5, 6, 7]:
        if f'{m}/' in date_str:
            month = m
            break
    if month is None:
        continue

    if month not in events_by_month:
        events_by_month[month] = []

    events_by_month[month].append({
        'name': event_name,
        'date': date_str,
        'place': place,
    })

# --- IG月別投稿を作成 ---
ig_monthly_rows = []
for month in sorted(events_by_month.keys()):
    events = events_by_month[month]
    month_name = {4: '4月', 5: '5月', 6: '6月', 7: '7月'}[month]

    lines = [f'【{month_name}のイベント一覧】', '', '━━━━━━━━━━━━━━━', '']
    for e in events:
        lines.append(f"📅 {e['date']}")
        lines.append(f"　{e['name']}")
        if e['place'] and e['place'] != '—' and e['place'] != '（要確認）':
            lines.append(f"　📍{e['place']}")
        lines.append('')

    lines.append('━━━━━━━━━━━━━━━')
    lines.append('')
    lines.append('各イベントの詳細は')
    lines.append('個別の投稿をご覧ください')
    lines.append('')
    lines.append('━━━━━━━━━━━━━━━')
    lines.append('▼ お申し込み・詳細はプロフィールから')
    lines.append('')
    lines.append(f'#KITAサウンドヒーリング #{month_name}イベント #自然音 #ウェルビーイング #サウンドヒーリング #体験 #セルフケア')

    caption = '\n'.join(lines)

    # 投稿予定日: 月初め
    post_dates = {4: '4/1', 5: '5/1', 6: '6/1', 7: '7/1'}

    ig_monthly_rows.append([
        f'M{month}',  # No
        f'{month_name}イベント一覧',
        'まとめ',
        month_name,
        '—',
        'まとめ投稿',
        caption,
        '単画像',
        f'{month_name}イベントカレンダー画像',
        '',  # 画像リンク
        '',  # 画像表示
        post_dates[month],
        '下書き',
        '✅',
        '',
        '',
    ])

# IGシートに追加
ig_next_row = len(ig_data) + 1
ig_end_row = ig_next_row + len(ig_monthly_rows) - 1
ig_ws.update(values=ig_monthly_rows, range_name=f'A{ig_next_row}:P{ig_end_row}', value_input_option='USER_ENTERED')
print(f"  IG: {len(ig_monthly_rows)}件の月別一覧を Row {ig_next_row}〜{ig_end_row} に追加")

# IG月別行のフォーマット（ヘッダーと差別化 - 薄い青背景）
monthly_format_requests = []
for idx in range(ig_next_row - 1, ig_end_row):
    monthly_format_requests.append({
        'repeatCell': {
            'range': {
                'sheetId': ig_sid,
                'startRowIndex': idx, 'endRowIndex': idx + 1,
                'startColumnIndex': 0, 'endColumnIndex': ig_cols,
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': {'red': 0.88, 'green': 0.93, 'blue': 1.0},
                }
            },
            'fields': 'userEnteredFormat.backgroundColor',
        }
    })
if monthly_format_requests:
    sh.batch_update({'requests': monthly_format_requests})

# --- X月別投稿を作成 ---
x_monthly_rows = []
for month in sorted(events_by_month.keys()):
    events = events_by_month[month]
    month_name = {4: '4月', 5: '5月', 6: '6月', 7: '7月'}[month]

    lines = [f'【{month_name}のイベント一覧】', '']
    for e in events:
        lines.append(f"📅{e['date']}")
        lines.append(f"　{e['name']}")
        lines.append('')

    lines.append('各イベントの詳細は固定ポストから')
    lines.append('')
    lines.append(f'#KITAサウンドヒーリング #{month_name}イベント')

    text = '\n'.join(lines)
    count = x_count(text)

    # 280文字に収まるか確認、超えたら短縮
    if count > 280:
        # イベント数が多い場合は場所省略版で再生成
        lines = [f'【{month_name}のイベント】', '']
        for e in events:
            lines.append(f"📅{e['date']} {e['name']}")
        lines.append('')
        lines.append('詳細は固定ポストから')
        lines.append(f'#KITAサウンドヒーリング #{month_name}')
        text = '\n'.join(lines)
        count = x_count(text)

    post_dates = {4: '4/1', 5: '5/1', 6: '6/1', 7: '7/1'}

    x_header_names = x_data[0]
    x_monthly_rows.append([
        f'{month_name}イベント一覧',
        'まとめ',
        month_name,
        '—',
        'まとめ投稿',
        text,
        f'{count}/280',
        '',
        '',  # 画像リンク
        '',  # 画像表示
        post_dates[month],
        '下書き',
        '',
        '',
    ])

# Xシートに追加
x_next_row = len(x_data) + 1
x_end_row = x_next_row + len(x_monthly_rows) - 1
x_ws.update(values=x_monthly_rows, range_name=f'A{x_next_row}:N{x_end_row}', value_input_option='USER_ENTERED')
print(f"  X: {len(x_monthly_rows)}件の月別一覧を Row {x_next_row}〜{x_end_row} に追加")

# X月別行もフォーマット
x_sid = x_ws.id
x_cols = len(x_data[0])
x_monthly_requests = []
for idx in range(x_next_row - 1, x_end_row):
    x_monthly_requests.append({
        'repeatCell': {
            'range': {
                'sheetId': x_sid,
                'startRowIndex': idx, 'endRowIndex': idx + 1,
                'startColumnIndex': 0, 'endColumnIndex': x_cols,
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 1.0},
                }
            },
            'fields': 'userEnteredFormat.backgroundColor',
        }
    })
# テキスト折り返し
for col in [5, 13]:
    x_monthly_requests.append({
        'repeatCell': {
            'range': {
                'sheetId': x_sid,
                'startRowIndex': x_next_row - 1, 'endRowIndex': x_end_row,
                'startColumnIndex': col, 'endColumnIndex': col + 1,
            },
            'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
            'fields': 'userEnteredFormat.wrapStrategy',
        }
    })
if x_monthly_requests:
    sh.batch_update({'requests': x_monthly_requests})

# X月別の文字数確認
print("\n=== X月別投稿 文字数確認 ===")
for row in x_monthly_rows:
    print(f"  {row[0]}: {row[6]}")

print("\n全完了!")
