#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Xイベント投稿シートを圭一郎さんのフィードバック(2026-04-09)に基づき修正+不足イベント追加"""

import gspread
import unicodedata

SPREADSHEET_ID = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"

def x_count(text):
    count = 0
    for c in text:
        if c == '\n':
            count += 1
        elif unicodedata.east_asian_width(c) in ('F', 'W'):
            count += 2
        else:
            count += 1
    return count

gc = gspread.service_account()
sh = gc.open_by_key(SPREADSHEET_ID)
ws = sh.worksheet("Xイベント投稿")

all_data = ws.get_all_values()
header = all_data[0]
col_idx = {h: i for i, h in enumerate(header)}

def col_letter(n):
    s = ''
    n += 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

updates = []

def update_cell(row_num, col_name, value):
    ci = col_idx[col_name]
    letter = col_letter(ci)
    updates.append((f'{letter}{row_num}', value))

# ============================================================
# 1. Row 2: オンライン体験講座 → 延期
# ============================================================
print("Row 2: オンライン体験講座 → 延期")
update_cell(2, 'ステータス', '延期')
update_cell(2, '確認', '4月延期→5月開始')
update_cell(2, 'メモ', '4/9フィードバック: 4月は延期。5月(5/19,5/21)からスタート、¥3,000')

# ============================================================
# 2. Row 8: 認定研修 第91期 → 第89期
# ============================================================
print("Row 8: 認定研修 第91期 → 第89期")
update_cell(8, 'イベント名', '認定研修 第89期')

text_r8 = """サウンドヒーリング
ファシリテーター認定研修会
第89期

📅6/12(金)〜14(日)

音の理論とケアの実技
自分軸を整える3日間

25年の実績ある認定プログラム

#KITAサウンドヒーリング #資格取得"""

update_cell(8, '投稿テキスト', text_r8)
update_cell(8, 'Xカウント', f'{x_count(text_r8)}/280')
update_cell(8, '確認', '修正済')
update_cell(8, 'メモ', '4/9フィードバック: 89期に修正（91期→89期）')

# ============================================================
# バッチ更新（既存行の修正）
# ============================================================
print(f"\n既存行修正: {len(updates)}セル更新中...")
batch = [{'range': rng, 'values': [[val]]} for rng, val in updates]
ws.batch_update(batch, value_input_option='USER_ENTERED')
print("既存行修正完了")

# ============================================================
# 3. 不足イベントを末尾に追加
# ============================================================
print("\n不足イベントを追加中...")

new_events = []

# --- カンガルーカップ ---
text_kc = """【協賛活動のお知らせ】
カンガルーカップ
国際女子オープンテニス 2026

📅4/28(火)〜5/2(土)
📍岐阜メモリアルセンター
🎾ITF国際女子テニス大会
👀観戦無料

世界ランキング100位以内を目指す
選手たちの登竜門

協会は選手の
サウンドヒーリングサポートを提供

#KITAサウンドヒーリング #カンガルーカップ"""

new_events.append({
    'event': 'カンガルーカップ 国際女子テニス',
    'category': '協賛イベント',
    'date': '4/28(火)〜5/2(土)',
    'place': '岐阜メモリアルセンター',
    'post_type': '事前告知',
    'text': text_kc,
    'media': '2025年大会写真（メール添付）',
    'post_date': '4/22頃',
    'memo': '活動紹介トーン。体験勧誘NG。公式: gifu-sports.org/gmc/kangaroocup2026/',
})

# --- オンラインWS 5月（初開催）---
text_ws5 = """【初開催】
音のウェルビーイング
オンライン体験ワークショップ

📅5/19(火) 10:00-12:00
📅5/21(木) 10:00-12:00
💻Zoom
💰¥3,000

自然音と呼吸で整えるセルフケア
今月から毎月開催スタート

#KITAサウンドヒーリング #オンライン講座"""

new_events.append({
    'event': 'オンラインWS 5月【初開催】',
    'category': 'オンライン講座',
    'date': '5/19(火), 5/21(木)',
    'place': 'Zoom',
    'post_type': '事前告知',
    'text': text_ws5,
    'media': 'オンライン講座イメージ',
    'post_date': '5/13頃',
    'memo': '5月初回、毎月開催、¥3,000。4月延期分の代替',
})

# --- 太陽食品コラボ 6月（2日間）---
text_ts = """太陽食品×サウンドヒーリング協会
「ここちよい音の日」第2弾

📅6/5(金), 6/6(土) 2日間
📍太陽食品 世田谷店
 （尾山台駅3分）
⏰13:00〜16:00
💰500円で体感音響ケア体験
🍵オーガニック飲料試飲付き

お子様連れも歓迎です

#KITAサウンドヒーリング #太陽食品"""

new_events.append({
    'event': '太陽食品コラボ 6月',
    'category': '太陽食品コラボ',
    'date': '6/5(金), 6/6(土)',
    'place': '太陽食品 世田谷店',
    'post_type': '事前告知',
    'text': text_ts,
    'media': '太陽食品チラシ / 4月コラボ写真',
    'post_date': '5/29頃',
    'memo': '4月と同じ形式。2日間開催',
})

# --- オンラインWS 6月 ---
text_ws6 = """音のウェルビーイング
オンライン体験ワークショップ

📅6/23(火) 10:00-12:00
📅6/25(木) 10:00-12:00
💻Zoom
💰¥3,000

自然音と呼吸で整えるセルフケア
毎月開催中

初めての方にもおすすめです

#KITAサウンドヒーリング #オンライン講座"""

new_events.append({
    'event': 'オンラインWS 6月',
    'category': 'オンライン講座',
    'date': '6/23(火), 6/25(木)',
    'place': 'Zoom',
    'post_type': '事前告知',
    'text': text_ws6,
    'media': 'オンライン講座イメージ',
    'post_date': '6/17頃',
    'memo': '毎月開催。¥3,000',
})

# --- 抗加齢医学学会 ---
text_ag = """【学会発表のお知らせ】

日本抗加齢医学学会にて
研究発表を行います

📅6/26(金)

テーマ:
自然音と都会音が
心身に与える影響の比較研究

音の影響を学術的に研究し
エビデンスに基づいた
サウンドヒーリングを推進しています

#KITAサウンドヒーリング #学会発表"""

new_events.append({
    'event': '抗加齢医学学会 学会発表',
    'category': '学会',
    'date': '6/26(金)',
    'place': '（要確認）',
    'post_type': '事前告知',
    'text': text_ag,
    'media': '過去の学会発表写真',
    'post_date': '6/20頃',
    'memo': '自然音vs都会音の実験結果発表。SNS告知OK',
})

# --- オンラインWS 7月 ---
text_ws7 = """音のウェルビーイング
オンライン体験ワークショップ

📅7/21(火) 10:00-12:00
📅7/23(木) 10:00-12:00
💻Zoom
💰¥3,000

自然音と呼吸で整えるセルフケア
毎月開催中

初めての方にもおすすめです

#KITAサウンドヒーリング #オンライン講座"""

new_events.append({
    'event': 'オンラインWS 7月',
    'category': 'オンライン講座',
    'date': '7/21(火), 7/23(木)',
    'place': 'Zoom',
    'post_type': '事前告知',
    'text': text_ws7,
    'media': 'オンライン講座イメージ',
    'post_date': '7/15頃',
    'memo': '毎月開催。¥3,000',
})

# 行追加
new_rows = []
for e in new_events:
    count = x_count(e['text'])
    # header: イベント名,カテゴリ,開催日,開催場所,投稿タイプ,投稿テキスト,Xカウント,メディア,画像リンク,画像表示,投稿予定日,ステータス,確認,メモ
    new_rows.append([
        e['event'],
        e['category'],
        e['date'],
        e['place'],
        e['post_type'],
        e['text'],
        f'{count}/280',
        e['media'],
        '',  # 画像リンク
        '',  # 画像表示
        e['post_date'],
        '下書き',
        '',
        e['memo'],
    ])

# 現在の最終行の次に追加
next_row = len(all_data) + 1
end_row = next_row + len(new_rows) - 1
range_str = f'A{next_row}:N{end_row}'
ws.update(values=new_rows, range_name=range_str, value_input_option='USER_ENTERED')
print(f"{len(new_rows)}件のイベントをRow {next_row}〜{end_row}に追加")

# 画像表示列にIMAGE関数を設定
img_formulas = []
for row in range(next_row, end_row + 1):
    formula = f'=IF(I{row}<>"", IMAGE(I{row}), "")'
    img_formulas.append([formula])
ws.update(values=img_formulas, range_name=f'J{next_row}:J{end_row}', value_input_option='USER_ENTERED')

# 新規行のテキスト折り返し設定
sheet_id = ws.id
requests = []
for col in [5, 13]:  # F(投稿テキスト), N(メモ)
    requests.append({
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': next_row - 1,
                'endRowIndex': end_row,
                'startColumnIndex': col,
                'endColumnIndex': col + 1,
            },
            'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
            'fields': 'userEnteredFormat.wrapStrategy',
        }
    })
sh.batch_update({'requests': requests})

print("\n完了!")
print("=" * 50)
print("既存行修正:")
print("  Row 2: オンライン体験講座 → 延期")
print("  Row 8: 認定研修 第91期 → 第89期")
print(f"\n新規追加 ({len(new_events)}件):")
for e in new_events:
    count = x_count(e['text'])
    print(f"  {e['event']} ({count}/280文字)")
