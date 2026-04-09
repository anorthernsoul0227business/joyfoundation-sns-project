#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""イベント投稿記事作成専用シートをX・Instagram用にそれぞれ作成"""

import gspread
import unicodedata

SPREADSHEET_ID = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"


def x_count(text):
    """X(Twitter)の文字数カウント（全角=2, 改行=1）"""
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

# ============================================================
# 1. Xイベント投稿専用シート
# ============================================================
X_SHEET_NAME = "Xイベント投稿"

try:
    x_ws = sh.add_worksheet(title=X_SHEET_NAME, rows=50, cols=12)
    print(f"[X] '{X_SHEET_NAME}' シート作成完了")
except Exception:
    x_ws = sh.worksheet(X_SHEET_NAME)
    x_ws.clear()
    print(f"[X] '{X_SHEET_NAME}' シートをクリアして再作成")

x_header = [
    'イベント名',        # A: イベント名称
    'カテゴリ',          # B: スターライト/ここちよい音の日/体験WS/研修/コラボ等
    '開催日',            # C: 日付
    '開催場所',          # D: 会場
    '投稿タイプ',        # E: 事前告知/リマインド/当日/レポート
    '投稿テキスト',      # F: 本文
    'Xカウント',         # G: 文字数/280
    'メディア',          # H: 画像・動画のメモ
    '投稿予定日',        # I: 投稿する日
    'ステータス',        # J: 下書き/確認済/投稿済
    '確認',              # K: 圭一郎さんチェック
    'メモ',              # L: 備考
]

x_rows = [x_header]

# --- Xイベント投稿サンプル ---
x_events = [
    {
        'event': 'オンライン体験講座',
        'category': 'オンライン講座',
        'date': '4/14(火), 4/23(木)',
        'place': 'Zoom',
        'post_type': '事前告知',
        'text': '【自宅から参加OK】\n音のウェルビーイング体験講座\n\nハワイや屋久島の自然音と\n呼吸で整えるセルフケア\n\n📅4/14(火) 10:00-12:00\n📅4/23(木) 10:00-12:00\n💻Zoom\n💰¥4,000\n\n初めての方にもおすすめです\n\n#KITAサウンドヒーリング #オンライン講座',
        'media': 'オンライン講座イメージ画像',
        'post_date': '4/10頃',
        'memo': '開催1週間前〜3日前に告知',
    },
    {
        'event': 'ここちよい音の日',
        'category': 'ここちよい音の日',
        'date': '4/18(土)',
        'place': '田園調布 長田整形外科',
        'post_type': '事前告知',
        'text': '毎月開催の無料体験会\n「ここちよい音の日」\n\n📅4/18(土)\n📍田園調布・長田整形外科\n⏰11:30〜14:00 体験\n⏰14:00〜 院長×理事長トーク\n💰無料・予約不要\n\n初めての方も気軽にどうぞ\n\n#KITAサウンドヒーリング #ここちよい音の日',
        'media': 'ここちよい音の日の写真',
        'post_date': '4/14頃',
        'memo': '毎月告知。写真は圭一郎さんから提供済み',
    },
    {
        'event': 'スターライトヒーリング さいたま',
        'category': 'スターライト',
        'date': '5/3(日), 5/10(日)',
        'place': 'さいたま市宇宙劇場',
        'post_type': '事前告知',
        'text': 'プラネタリウムで\n沖縄・屋久島の自然音を体感\n\nスターライトヒーリング\n\n📅5/3(日) 13:30〜\n📅5/10(日) 13:30〜\n📍さいたま市宇宙劇場\n⏱約50分\n\nGW、ちょっと特別な体験を\n\n#スターライトヒーリング #GW',
        'media': 'プラネタリウム写真',
        'post_date': '4/25頃',
        'memo': 'GWに合わせた訴求',
    },
    {
        'event': 'スターライトヒーリング 仙台',
        'category': 'スターライト',
        'date': '5/11, 5/18, 5/25(土)',
        'place': '仙台市天文台',
        'post_type': '事前告知',
        'text': 'スターライトヒーリング\n仙台市天文台\n\n📅5/11(土) 19:40〜\n📅5/18(土) 19:40〜\n📅5/25(土) 19:40〜\n📍仙台市天文台\n⏱約50分\n\nプラネタリウムで\nハワイの星空×自然音を体感\n\n#スターライトヒーリング #仙台',
        'media': '仙台市天文台写真',
        'post_date': '5/5頃',
        'memo': '東北エリアのフォロワー向け',
    },
    {
        'event': '体験WS 自由が丘',
        'category': '体験WS',
        'date': '5/14(木)',
        'place': '自由が丘lab',
        'post_type': '事前告知',
        'text': '3つのここちよい音\n体験ワークショップ\n\n📅5/14(木)\n⏰午前10:30 / 午後13:30\n📍自由が丘lab\n\n自然音・体感音響・呼吸と声\n2時間でじっくり体験できます\n\n初めての方にもおすすめ\n\n#KITAサウンドヒーリング #体験WS',
        'media': '自由が丘lab写真',
        'post_date': '5/8頃',
        'memo': '',
    },
    {
        'event': 'ここちよい音の日',
        'category': 'ここちよい音の日',
        'date': '5/16(土)',
        'place': '田園調布 長田整形外科',
        'post_type': '事前告知',
        'text': '「ここちよい音の日」\n5月は16日(土)開催\n\n📍田園調布・長田整形外科\n⏰11:30〜14:00 体験\n⏰14:00〜 院長×理事長トーク\n💰無料・予約不要\n\n自然音と体感音響を\n気軽に体験できます\n\n#KITAサウンドヒーリング #ここちよい音の日',
        'media': 'ここちよい音の日写真',
        'post_date': '5/12頃',
        'memo': '',
    },
    {
        'event': '認定研修 第91期',
        'category': '資格認定研修',
        'date': '6/12(金)〜14(日)',
        'place': '—',
        'post_type': '事前告知',
        'text': 'サウンドヒーリング\nファシリテーター認定研修会\n第91期\n\n📅6/12(金)〜14(日)\n\n音の理論とケアの実技\n自分軸を整える3日間\n\n25年の実績ある認定プログラム\n\n#KITAサウンドヒーリング #資格取得',
        'media': '研修会写真',
        'post_date': '5月下旬',
        'memo': '',
    },
]

for e in x_events:
    count = x_count(e['text'])
    x_rows.append([
        e['event'],
        e['category'],
        e['date'],
        e['place'],
        e['post_type'],
        e['text'],
        f"{count}/280",
        e['media'],
        e['post_date'],
        '下書き',
        '',
        e['memo'],
    ])

x_ws.update(x_rows, 'A1')
print(f"[X] {len(x_rows)-1}件のイベント投稿を書き込み")

# ヘッダーフォーマット（ダークブルー — 通常X投稿シートと同系統）
x_ws.format('A1:L1', {
    'backgroundColor': {'red': 0.05, 'green': 0.15, 'blue': 0.55},
    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True},
})

x_requests = []
x_sid = x_ws.id
x_widths = [140, 100, 130, 160, 80, 400, 70, 180, 80, 70, 60, 200]
for i, w in enumerate(x_widths):
    x_requests.append({
        'updateDimensionProperties': {
            'range': {'sheetId': x_sid, 'dimension': 'COLUMNS', 'startIndex': i, 'endIndex': i + 1},
            'properties': {'pixelSize': w},
            'fields': 'pixelSize',
        }
    })
x_requests.append({
    'updateSheetProperties': {
        'properties': {'sheetId': x_sid, 'gridProperties': {'frozenRowCount': 1}},
        'fields': 'gridProperties.frozenRowCount',
    }
})
# 投稿テキスト列(F)とメモ列(L)を折り返し
for col_idx in [5, 11]:
    x_requests.append({
        'repeatCell': {
            'range': {'sheetId': x_sid, 'startRowIndex': 1, 'startColumnIndex': col_idx, 'endColumnIndex': col_idx + 1},
            'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
            'fields': 'userEnteredFormat.wrapStrategy',
        }
    })

# ============================================================
# 2. Instagramイベント投稿専用シート
# ============================================================
IG_SHEET_NAME = "IGイベント投稿"

try:
    ig_ws = sh.add_worksheet(title=IG_SHEET_NAME, rows=50, cols=13)
    print(f"[IG] '{IG_SHEET_NAME}' シート作成完了")
except Exception:
    ig_ws = sh.worksheet(IG_SHEET_NAME)
    ig_ws.clear()
    print(f"[IG] '{IG_SHEET_NAME}' シートをクリアして再作成")

ig_header = [
    'No',                # A
    'イベント名',        # B
    'カテゴリ',          # C
    '開催日',            # D
    '開催場所',          # E
    '投稿タイプ',        # F: 事前告知/リマインド/当日/レポート
    'キャプション',      # G: 本文
    '形式',              # H: カルーセル/単画像/リール
    '画像メモ',          # I
    '投稿予定日',        # J
    'ステータス',        # K
    '確認',              # L
    'メモ',              # M
]

ig_rows = [ig_header]

ig_events = [
    {
        'event': 'オンライン体験講座',
        'category': 'オンライン講座',
        'date': '4/14(火), 4/23(木)',
        'place': 'Zoom',
        'post_type': '事前告知',
        'caption': '【自宅から参加できる音のウェルビーイング体験】\n\n━━━━━━━━━━━━━━━\n\nハワイや屋久島の自然音と呼吸で\n心と体を整えるオンライン講座\n\n━━━━━━━━━━━━━━━\n\n📅 4/14(火) 10:00-12:00\n📅 4/23(木) 10:00-12:00\n💻 Zoom開催\n💰 ¥4,000\n\nスピーカーから流れる自然音を\n体全体で感じる体験です\n\n初めての方にもおすすめ\nお気軽にご参加ください\n\n━━━━━━━━━━━━━━━\n▼ お申し込みはプロフィールから\n\n#KITAサウンドヒーリング #オンライン講座 #自然音 #ウェルビーイング #セルフケア #呼吸法 #リラックス #ハワイ #屋久島 #おうち時間 #音のある暮らし #体験講座',
        'format': 'カルーセル',
        'image_memo': 'オンライン講座イメージ / 自然風景',
        'post_date': '4/10頃',
        'memo': '開催1週間前〜3日前に告知',
    },
    {
        'event': 'ここちよい音の日',
        'category': 'ここちよい音の日',
        'date': '4/18(土)',
        'place': '田園調布 長田整形外科',
        'post_type': '事前告知',
        'caption': '【毎月開催｜無料体験会】\nここちよい音の日\n\n━━━━━━━━━━━━━━━\n\n📅 4/18(土)\n📍 田園調布・長田整形外科\n⏰ 11:30〜14:00 体験\n⏰ 14:00〜 院長×理事長トーク\n💰 無料・予約不要\n\n━━━━━━━━━━━━━━━\n\n自然音と体感音響を\n気軽に体験できる月1回の特別な日\n\n「気づいたら眠ってた」\n「肩の力が抜けた」\nそんな声をいただいています\n\n初めての方も気軽にお越しください\n\n━━━━━━━━━━━━━━━\n▼ 詳しくはプロフィールから\n\n#KITAサウンドヒーリング #ここちよい音の日 #長田整形外科 #田園調布 #無料体験 #予防医療 #自然音 #体感音響 #毎月開催 #予約不要 #セルフケア #リラックス',
        'format': 'カルーセル',
        'image_memo': 'ここちよい音の日の会場写真',
        'post_date': '4/14頃',
        'memo': '毎月告知。写真は圭一郎さんから提供済み',
    },
    {
        'event': 'スターライトヒーリング さいたま',
        'category': 'スターライト',
        'date': '5/3(日), 5/10(日)',
        'place': 'さいたま市宇宙劇場',
        'post_type': '事前告知',
        'caption': '【プラネタリウムで自然音体験】\nスターライトヒーリング\n\n━━━━━━━━━━━━━━━\n\n📅 5/3(日) 13:30〜\n📅 5/10(日) 13:30〜\n📍 さいたま市宇宙劇場\n⏱ 約50分\n\n━━━━━━━━━━━━━━━\n\n満天の星空の下\n沖縄・屋久島の自然音に包まれる\n累計6,400名以上が体験した\n人気プログラム\n\nGW、ちょっと特別な体験を\n\n━━━━━━━━━━━━━━━\n▼ チケット情報はプロフィールから\n\n#スターライトヒーリング #プラネタリウム #さいたま市宇宙劇場 #自然音 #GW #ゴールデンウィーク #沖縄 #屋久島 #KITAサウンドヒーリング #体験 #癒し #星空',
        'format': 'カルーセル',
        'image_memo': 'プラネタリウム内の写真',
        'post_date': '4/25頃',
        'memo': 'GWに合わせた訴求。映える写真を使用',
    },
    {
        'event': 'スターライトヒーリング 仙台',
        'category': 'スターライト',
        'date': '5/11, 5/18, 5/25(土)',
        'place': '仙台市天文台',
        'post_type': '事前告知',
        'caption': '【仙台でも開催中】\nスターライトヒーリング\n仙台市天文台 特別公演\n\n━━━━━━━━━━━━━━━\n\n📅 5/11(土) 19:40〜\n📅 5/18(土) 19:40〜\n📅 5/25(土) 19:40〜\n📍 仙台市天文台\n⏱ 約50分\n\n━━━━━━━━━━━━━━━\n\nプラネタリウムの満天の星の下\nハワイの自然音に包まれる時間\n\n東北の皆さま、ぜひ\n\n━━━━━━━━━━━━━━━\n▼ 詳しくはプロフィールから\n\n#スターライトヒーリング #仙台市天文台 #仙台 #プラネタリウム #ハワイ #自然音 #KITAサウンドヒーリング #東北 #体験 #癒し #星空 #特別公演',
        'format': 'カルーセル',
        'image_memo': '仙台市天文台の写真',
        'post_date': '5/5頃',
        'memo': '東北エリア向け',
    },
    {
        'event': '体験WS 自由が丘',
        'category': '体験WS',
        'date': '5/14(木)',
        'place': '自由が丘lab',
        'post_type': '事前告知',
        'caption': '【3つのここちよい音 体験WS】\n\n━━━━━━━━━━━━━━━\n\n📅 5/14(木)\n⏰ 午前10:30 / 午後13:30\n📍 自由が丘lab\n\n━━━━━━━━━━━━━━━\n\n自然音・体感音響・呼吸と声\n3つの音を2時間でじっくり体験\n\n「サウンドヒーリングって何？」\nという方にぴったりの内容です\n\n初めての方もお気軽にどうぞ\n\n━━━━━━━━━━━━━━━\n▼ お申し込みはプロフィールから\n\n#KITAサウンドヒーリング #体験ワークショップ #自由が丘 #自然音 #体感音響 #呼吸 #セルフケア #音のある暮らし #初めて歓迎 #リラックス #癒し #ウェルビーイング',
        'format': 'カルーセル',
        'image_memo': '自由が丘lab / WS風景写真',
        'post_date': '5/8頃',
        'memo': '',
    },
    {
        'event': 'ここちよい音の日',
        'category': 'ここちよい音の日',
        'date': '5/16(土)',
        'place': '田園調布 長田整形外科',
        'post_type': '事前告知',
        'caption': '【毎月開催｜無料体験会】\nここちよい音の日\n\n━━━━━━━━━━━━━━━\n\n📅 5/16(土)\n📍 田園調布・長田整形外科\n⏰ 11:30〜14:00 体験\n⏰ 14:00〜 院長×理事長トーク\n💰 無料・予約不要\n\n━━━━━━━━━━━━━━━\n\n自然音と体感音響を\n気軽に体験できます\n\nお気軽にお越しください\n\n━━━━━━━━━━━━━━━\n▼ 詳しくはプロフィールから\n\n#KITAサウンドヒーリング #ここちよい音の日 #長田整形外科 #田園調布 #無料体験 #予防医療 #自然音 #体感音響 #毎月開催 #予約不要 #セルフケア #リラックス',
        'format': 'カルーセル',
        'image_memo': 'ここちよい音の日写真',
        'post_date': '5/12頃',
        'memo': '',
    },
    {
        'event': '認定研修 第91期',
        'category': '資格認定研修',
        'date': '6/12(金)〜14(日)',
        'place': '—',
        'post_type': '事前告知',
        'caption': '【音のプロを目指す方へ】\nファシリテーター認定研修会 第91期\n\n━━━━━━━━━━━━━━━\n\n📅 6/12(金)〜14(日)\n\n音の理論とケアの実技\n自分軸を整える3日間のプログラム\n\n━━━━━━━━━━━━━━━\n\n25年の実績ある認定プログラム\n\nサウンドヒーリングを\nご自身のお仕事に活かしたい方\nまずはお気軽にお問い合わせください\n\n━━━━━━━━━━━━━━━\n▼ 詳しくはプロフィールから\n\n#KITAサウンドヒーリング #資格取得 #認定研修 #ファシリテーター #セルフケア #スキルアップ #音の仕事 #キャリア #ウェルビーイング #自然音 #学び #新しい挑戦',
        'format': 'カルーセル',
        'image_memo': '研修会の様子 / 修了証',
        'post_date': '5月下旬',
        'memo': '',
    },
]

for i, e in enumerate(ig_events, 1):
    ig_rows.append([
        i,
        e['event'],
        e['category'],
        e['date'],
        e['place'],
        e['post_type'],
        e['caption'],
        e['format'],
        e['image_memo'],
        e['post_date'],
        '下書き',
        '',
        e['memo'],
    ])

ig_ws.update(ig_rows, 'A1')
print(f"[IG] {len(ig_rows)-1}件のイベント投稿を書き込み")

# ヘッダーフォーマット（Instagram系のオレンジ — 通常IGシートと差別化）
ig_ws.format('A1:M1', {
    'backgroundColor': {'red': 0.95, 'green': 0.45, 'blue': 0.15},
    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True},
})

ig_requests = []
ig_sid = ig_ws.id
ig_widths = [40, 140, 100, 130, 160, 80, 400, 80, 150, 80, 70, 60, 200]
for i, w in enumerate(ig_widths):
    ig_requests.append({
        'updateDimensionProperties': {
            'range': {'sheetId': ig_sid, 'dimension': 'COLUMNS', 'startIndex': i, 'endIndex': i + 1},
            'properties': {'pixelSize': w},
            'fields': 'pixelSize',
        }
    })
ig_requests.append({
    'updateSheetProperties': {
        'properties': {'sheetId': ig_sid, 'gridProperties': {'frozenRowCount': 1}},
        'fields': 'gridProperties.frozenRowCount',
    }
})
# キャプション列(G)とメモ列(M)を折り返し
for col_idx in [6, 12]:
    ig_requests.append({
        'repeatCell': {
            'range': {'sheetId': ig_sid, 'startRowIndex': 1, 'startColumnIndex': col_idx, 'endColumnIndex': col_idx + 1},
            'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
            'fields': 'userEnteredFormat.wrapStrategy',
        }
    })

# ============================================================
# バッチ更新を一括実行
# ============================================================
all_requests = x_requests + ig_requests
sh.batch_update({'requests': all_requests})
print("\nフォーマット適用完了!")
print("=" * 40)
print(f"✔ '{X_SHEET_NAME}' — {len(x_rows)-1}件")
print(f"✔ '{IG_SHEET_NAME}' — {len(ig_rows)-1}件")
print("Done!")
