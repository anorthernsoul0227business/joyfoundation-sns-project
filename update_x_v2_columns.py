#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X投稿v2シートにリプ投稿列と画像列を追加し、イベント告知を充実させる"""

import gspread
import unicodedata

def x_count(text):
    count = 0
    for c in text:
        if c == '\n': count += 1
        elif unicodedata.east_asian_width(c) in ('F', 'W'): count += 2
        else: count += 1
    return count

gc = gspread.service_account()
sh = gc.open_by_key("1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")
ws = sh.worksheet("X投稿v2")

# Get all current data
all_data = ws.get_all_values()

# New column order:
# Day | 投稿タイプ | 投稿テキスト | 画像/動画 | リプ投稿 | Xカウント | メディアメモ | 投稿時間 | ステータス | 確認 | メモ
new_header = ['Day', '投稿タイプ', '投稿テキスト', '画像/動画', 'リプ投稿（リンク・補足）', 'Xカウント', '投稿時間', 'ステータス', '確認', 'メモ']

# Rebuild all rows with new columns
new_rows = [new_header]

# Row data: old format was [Day, Type, Text, XCount, Media, Time, Status, Check, Memo]
for i, row in enumerate(all_data[1:], 1):
    day = row[0] if len(row) > 0 else ''
    typ = row[1] if len(row) > 1 else ''
    text = row[2] if len(row) > 2 else ''
    xcount = row[3] if len(row) > 3 else ''
    media = row[4] if len(row) > 4 else ''
    time = row[5] if len(row) > 5 else ''
    status = row[6] if len(row) > 6 else ''
    check = row[7] if len(row) > 7 else ''
    memo = row[8] if len(row) > 8 else ''

    # Create reply text for events
    reply = ''
    if '太陽食品' in day:
        reply = '▼ 詳細・アクセス\nhttps://www.sound-healing.jp/\n\n尾山台駅から徒歩3分\nオーガニック食品とここちよい音\n体の外と内、両方からのケアを気軽に体験できます\n\nお子様連れも歓迎です'
    elif '認定研修' in day and '90' in day:
        reply = '▼ 詳細・お申込み\nhttps://www.sound-healing.jp/\n\n音の理論、ケアの実技、自分軸を整える内容\n修了後はファシリテーターとして活動可能\n\nこれまで2,000名以上が受講'
    elif 'スターライト' in day and 'さいたま' in day and '4/12' in day:
        reply = '▼ 詳細・お申込み\nhttps://www.sound-healing.jp/starlight-healing_malama_hawaii_2025-2026.html\n\nハワイで収録した波・風・鳥の声を\nプラネタリウムのドームで立体的に体感\n\n累計21,000名以上にご参加いただいています'
    elif 'オンライン' in day:
        reply = '▼ お申込み\nhttps://www.sound-healing.jp/\n\nハワイや屋久島で収録した世界の自然音を使った体験\n呼吸と声のセルフケアも学べます\n\n初めての方にもわかりやすい内容です'
    elif 'スターライト' in day and '仙台' in day and '4月' in day:
        reply = '▼ 詳細\nhttps://www.sendai-astro.jp/planetarium/\n\nプラネタリウムのドームいっぱいに広がる\nハワイの星空と自然音\n\n土曜の夜、特別な50分を'
    elif '体験WS' in day and '4/16' in day:
        reply = '▼ 詳細・お申込み\nhttps://www.sound-healing.jp/workshop.html\n\n自然音・体感音響・呼吸と声の3つを\n2時間でじっくり体験\n\n4/16は満席のため5/14をおすすめします'
    elif 'ここちよい音の日' in day and '4/18' in day:
        reply = '▼ 詳細\nhttps://www.sound-healing.jp/\n\n自然音BGMの中で体感音響クッションを体験\n14:00からは長田院長と喜田理事長のトークも\n\n「サウンドヒーリングって何？」という方にこそ来ていただきたいイベントです'
    elif 'スターライト' in day and 'さいたま' in day and '5月' in day:
        reply = '▼ 詳細・お申込み\nhttps://www.sound-healing.jp/\n\n5月は沖縄・屋久島の自然音プログラム\nGW、いつもと違う特別な体験を'
    elif 'スターライト' in day and '仙台' in day and '5月' in day:
        reply = '▼ 詳細\nhttps://www.sendai-astro.jp/planetarium/\n\n毎週土曜の夜、仙台市天文台で\nハワイの星空×自然音を体感'
    elif '体験WS' in day and '5/14' in day:
        reply = '▼ 詳細・お申込み\nhttps://www.sound-healing.jp/workshop.html\n\n自然音・体感音響・呼吸と声の3つを\n2時間でじっくり体験できます\n\n午前・午後の2回開催'
    elif 'ここちよい音の日' in day and '5/16' in day:
        reply = '▼ 詳細\nhttps://www.sound-healing.jp/\n\n毎月開催の無料体験会\n予約不要でお気軽にお越しください'
    elif '認定研修' in day and '91' in day:
        reply = '▼ 詳細・お申込み\nhttps://www.sound-healing.jp/\n\n音の理論とケアの実技を3日間で学びます\n修了後はファシリテーターとして活動可能'
    elif day == '固定':
        reply = '▼ 公式サイト\nhttps://www.sound-healing.jp/\n\n▼ イベント一覧・お申込み\nhttps://www.sound-healing.jp/\n\n自然音・体感音響・呼吸と声\n3つのメソッドで心と体のバランスを整えます'
    elif 'Day1' in day:
        reply = '1/fゆらぎについて詳しくはこちら\nhttps://www.sound-healing.jp/\n\n私たちは複数の学会で\n音が心と体に与える影響を研究発表しています'
    elif 'Day2' in day:
        reply = '自然音を試してみたい方へ\n\n▼ YouTubeチャンネル\nhttps://www.youtube.com/@harmonicscience2651\n\nまずはスピーカーで小さく流してみてください'
    elif 'Day3' in day:
        reply = '「体で聴く」体感音響を体験できるイベント\n\n▼ 毎月開催・無料体験会\nhttps://www.sound-healing.jp/\n\n百聞は一「体感」にしかず'
    elif 'Day4' in day:
        reply = '▼「ここちよい音の日」詳細\nhttps://www.sound-healing.jp/\n\n📍田園調布・長田整形外科\n毎月1回土曜日開催\n予約不要・無料'
    elif 'Day5' in day:
        reply = '自然音の選び方に正解はありません\nあなたが心地いいと感じるものが答えです\n\n▼ YouTubeで試聴\nhttps://www.youtube.com/@harmonicscience2651'

    new_rows.append([day, typ, text, media, reply, xcount, time, status, check, memo])

# Clear and rewrite
ws.clear()
ws.update(new_rows, 'A1')
print(f"Rewrote {len(new_rows)-1} rows with new columns")

# Format header
ws.format('A1:J1', {
    'backgroundColor': {'red': 0.1, 'green': 0.1, 'blue': 0.5},
    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True}
})

# Column widths
requests = []
sheet_id = ws.id
widths = [120, 90, 350, 150, 300, 70, 80, 60, 50, 200]
for i, w in enumerate(widths):
    requests.append({
        'updateDimensionProperties': {
            'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': i, 'endIndex': i+1},
            'properties': {'pixelSize': w},
            'fields': 'pixelSize'
        }
    })
requests.append({
    'updateSheetProperties': {
        'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}},
        'fields': 'gridProperties.frozenRowCount'
    }
})
# Wrap text columns: 投稿テキスト(C), 画像/動画(D), リプ投稿(E), メモ(J)
for col_idx in [2, 3, 4, 9]:
    requests.append({
        'repeatCell': {
            'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': col_idx, 'endColumnIndex': col_idx+1},
            'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
            'fields': 'userEnteredFormat.wrapStrategy'
        }
    })
sh.batch_update({'requests': requests})
print("Formatting applied!")
print("Done!")
