#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNSアカウント一覧シートをGoogle Sheetsに追加"""

import gspread

gc = gspread.service_account()
sh = gc.open_by_key("1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")

# Create new worksheet
try:
    ws = sh.add_worksheet(title="SNSアカウント一覧", rows=30, cols=10)
    print("Sheet created")
except:
    ws = sh.worksheet("SNSアカウント一覧")
    ws.clear()
    print("Sheet cleared")

header = ['SNS', 'アカウント名', 'URL', '登録メール', '用途', 'アカウント種別', '作成日', 'セットアップ状況', 'API連携', 'メモ']
rows = [header]

rows.append([
    'X（Twitter）',
    '@SFH_Science',
    'https://x.com/SFH_Science',
    '（要確認）',
    '日常Tips・イベント告知・記事シェア',
    '通常アカウント',
    '',
    'プロフィール設定済み',
    'API連携済み（OAuth 1.0）',
    '投稿頻度: 毎日'
])

rows.append([
    'Instagram',
    '@harmonicscience_jp',
    'https://www.instagram.com/harmonicscience_jp/',
    '（要確認）',
    'カルーセル・リール・ビジュアル訴求',
    'ビジネスアカウント（Health & wellness website）',
    '2026-02-24',
    'プロフィール設定済み / Webリンク未設定（モバイルから必要）',
    'FBページ管理者権限が必要→保留',
    '投稿頻度: 週4回'
])

rows.append([
    'YouTube',
    '@harmonicscience2651',
    'https://www.youtube.com/@harmonicscience2651',
    '（要確認）',
    '自然音BGM・解説動画・実践ガイド',
    'チャンネル',
    '',
    'チャンネル作成済み / アート・概要欄・リンク未設定',
    '',
    '投稿頻度: 週2回予定 / 無料長時間BGM配信（睡眠用3時間等）'
])

rows.append([
    '公式LINE',
    'サウンドヒーリング協会',
    'https://line.me/R/ti/p/@868hqnfw',
    '（要確認）',
    'ステップ配信・限定情報・イベント告知',
    '公式アカウント / LINE ID: @868hqnfw',
    '2026-02-24',
    'アカウント作成済み / あいさつメッセージ・リッチメニュー・ステップ配信未設定',
    'ログイン情報確認待ち',
    '管理画面: https://manager.line.biz/'
])

rows.append([
    'note',
    '（未作成）',
    '',
    '',
    '長文記事・有料コンテンツ',
    '',
    '',
    '未作成',
    '',
    '基本無料 / 有料はセルフケアプログラム等の補助的位置づけ'
])

rows.append([
    'Facebook',
    'サウンドヒーリング協会',
    'https://www.facebook.com/harmonicscience/',
    '',
    '既存会員向け情報発信',
    'Facebookページ（602フォロワー）',
    '',
    '圭一郎さんのFBアカウント乗っ取り被害でアクセス不可',
    '',
    '当面スキップ / Instagram手動投稿で対応'
])

rows.append([
    '公式サイト（協会）',
    'サウンドヒーリング協会',
    'https://www.sound-healing.jp/',
    '',
    'メインサイト',
    'NPO法人',
    '2001年設立',
    '運用中',
    '',
    ''
])

rows.append([
    '公式サイト（JF）',
    'ジョイファンデーション',
    'https://www.h-garden.com/',
    '',
    '法人サイト',
    '株式会社',
    '1993年設立',
    '運用中',
    '',
    '代表: 喜田圭一郎 / 所在地: 自由が丘 Healing Garden'
])

# Write data
ws.update(rows, 'A1')
print(f"Wrote {len(rows)-1} rows")

# Format header (dark green)
ws.format('A1:J1', {
    'backgroundColor': {'red': 0.15, 'green': 0.42, 'blue': 0.24},
    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True}
})

# Batch formatting
requests = []
sheet_id = ws.id
widths = [100, 160, 250, 120, 200, 180, 90, 200, 150, 250]
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
# Wrap all cells
requests.append({
    'repeatCell': {
        'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'endRowIndex': len(rows), 'startColumnIndex': 0, 'endColumnIndex': 10},
        'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
        'fields': 'userEnteredFormat.wrapStrategy'
    }
})
sh.batch_update({'requests': requests})
print("Formatting applied!")
print("Done!")
