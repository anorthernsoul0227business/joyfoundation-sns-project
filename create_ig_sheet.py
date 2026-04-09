#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instagram投稿スケジュールをGoogle Sheetsに追加"""

import gspread

gc = gspread.service_account()
sh = gc.open_by_key("1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")

# Create new worksheet for Instagram
try:
    ig_ws = sh.add_worksheet(title="Instagram", rows=50, cols=10)
    print("Instagram sheet created")
except:
    ig_ws = sh.worksheet("Instagram")
    ig_ws.clear()
    print("Instagram sheet cleared")

header = ['No', 'カテゴリ', 'タイトル', 'キャプション', '形式', '画像メモ', 'ステータス', '予定日', '確認', 'メモ']
rows = [header]

# 基礎知識カルーセル Day 1-6
rows.append([1, '基礎知識', 'Day1: 自己紹介', '（投稿プランv3で完成済み）', 'カルーセル5枚', '既存素材', '下書き', '', '', ''])

rows.append([2, '基礎知識', 'Day2: サウンドヒーリングって怪しくない？',
    '【サウンドヒーリングって怪しくない？】\nそう思った方にこそ読んでほしい。\n\n━━━━━━━━━━━━━━━\n\n「音で癒し」と聞くと\nちょっと構えてしまう方もいるかもしれません。\n\nでも、川の音を聴いてホッとしたり\n雨音で眠くなったり──\nそれも立派なサウンドヒーリングです。\n\n━━━━━━━━━━━━━━━\n\n私たちは25年間、学会での研究発表や\n企業・医療機関への導入を通じて\n音の可能性を探求してきました。\n\n━━━━━━━━━━━━━━━\n▼ まずは無料体験会へ\n\n#KITAサウンドヒーリング #サウンドヒーリングとは #自然音 #科学的根拠 #学会発表 #25年の実績 #怪しくない #音の力 #セルフケア #ウェルビーイング #心と体 #リラックス',
    'カルーセル5枚', '要デザイン', '下書き', '', '', ''])

rows.append([3, '基礎知識', 'Day3: YouTubeの自然音BGMと何が違う？',
    '【YouTubeの自然音BGMと何が違う？】\n\n━━━━━━━━━━━━━━━\n\n違いは「収録の仕方」にあります。\n\n収録家の中田悟は\n10年以上にわたり世界各地で自然音を収録してきました。\n\nただマイクを置くのではなく\nその場所の空気感ごとまるごと頂いてくる。\n\n━━━━━━━━━━━━━━━\n▼ 体験イベントはプロフィールから\n\n#KITAサウンドヒーリング #自然音 #自然音BGM #ハワイ #屋久島 #沖縄 #白神山地 #音のある暮らし #収録 #こだわり #リラックス #癒しの音',
    'カルーセル5枚', '収録地の風景写真', '下書き', '', '', ''])

rows.append([4, '基礎知識', 'Day4: 音を体で聴く 体感音響の世界',
    '【音を「体で聴く」って？】\n\n━━━━━━━━━━━━━━━\n\n人の体の約70%は水分。\n音の振動は水中を空気の約4倍の速さで伝わります。\nつまり、体全体が「耳」。\n\n━━━━━━━━━━━━━━━\n\n体感音響は専用のクッションを体にあてて\n全身で音を浴びる体験です。\n\n百聞は一「体感」にしかず。\n\n━━━━━━━━━━━━━━━\n▼ イベント詳細はプロフィールから\n\n#KITAサウンドヒーリング #体感音響 #KitaBiosonicPeaceMachine #音の振動 #全身で聴く #リラックス #セルフケア #体験会 #無料体験 #自然音 #癒し #音のある暮らし',
    'カルーセル5枚', '体感音響クッション写真', '下書き', '', '', ''])

rows.append([5, '基礎知識', 'Day5: なぜ整形外科で音の体験会？',
    '【なぜ整形外科で「音」の体験会？】\n\n━━━━━━━━━━━━━━━\n\n長田整形外科の長田夏哉院長は\n「病気にならない体をつくる」予防医療に取り組んでいます。\n\n「ここちよい音の日」は予約不要・参加無料。\n\n━━━━━━━━━━━━━━━\n▼ 詳しくはプロフィールから\n\n#KITAサウンドヒーリング #ここちよい音の日 #長田整形外科 #田園調布 #無料体験 #予防医療 #整形外科 #毎月開催 #予約不要 #セルフケア #自然音 #体感音響',
    'カルーセル5枚', '長田整形外科/ここちよい音の日写真', '下書き', '', '', ''])

rows.append([6, '基礎知識', 'Day6: 1/fゆらぎって聞いたことありますか？',
    '【1/fゆらぎって聞いたことありますか？】\n\n━━━━━━━━━━━━━━━\n\n波の音、ろうそくの炎、心臓の鼓動──\n自然界のここちよいものには「1/fゆらぎ」という共通のリズムが。\n\n━━━━━━━━━━━━━━━\n▼ まずは体験してみませんか？\n\n#KITAサウンドヒーリング #1fゆらぎ #自然音 #科学 #研究 #学会発表 #心地よさ #リラックス #波の音 #セルフケア #ウェルビーイング #自然のリズム',
    'カルーセル5枚', '波形グラフ+自然の例', '下書き', '', '', ''])

# 投稿プラン IG投稿
rows.append([7, 'Tips', '3/17 1/fゆらぎの秘密',
    '【なぜ自然音は心地いい？】\n1/fゆらぎの秘密\n\n川のせせらぎ、鳥のさえずり、波の音…\nなぜ私たちは自然の音に癒されるのでしょうか？\nその秘密は「1/fゆらぎ」にあります。\n\nまずは5分、お気に入りの自然音を聴いてみませんか？\n\n#1fゆらぎ #自然音 #倍音 #KITAサウンドヒーリング #セルフケア #リラックス #癒しの音',
    'カルーセル', '屋久島の森', '下書き', '3/17', '', ''])

rows.append([8, 'Tips', '3/19 体は70%水分 音の振動',
    '人体の約70%は水分。\n音は振動。水中では空気中の4倍以上の速さで伝わります。\n\nつまり、私たちの体は音を伝えやすい構造。\n\nまずは寝る前の5分、自然音を聴く時間をつくってみませんか？\n\n#自然音 #体は70%水分 #音の振動 #セルフケア #KITAサウンドヒーリング #リラックス #睡眠 #癒し',
    '単画像', '宮古島のビーチ', '下書き', '3/19', '', ''])

rows.append([9, 'Tips', '3/21 自然音で眠りの質を整えるヒント',
    '【寝つきが悪い方へ】\n自然音で眠りの質を整えるヒント\n\n（詳細は投稿プランHTMLに記載）\n\n#自然音 #睡眠 #KITAサウンドヒーリング',
    'カルーセル', '屋久島の月夜', '下書き', '3/21', '', ''])

# Write data
ig_ws.update(rows, 'A1')
print(f"Wrote {len(rows)-1} rows to Instagram sheet")

# Format header (Instagram pink/gradient)
ig_ws.format('A1:J1', {
    'backgroundColor': {'red': 0.88, 'green': 0.24, 'blue': 0.38},
    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True}
})

# Batch formatting
requests = []
sheet_id = ig_ws.id
widths = [40, 80, 220, 400, 80, 120, 70, 70, 60, 150]
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
requests.append({
    'repeatCell': {
        'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 3, 'endColumnIndex': 4},
        'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
        'fields': 'userEnteredFormat.wrapStrategy'
    }
})
sh.batch_update({'requests': requests})
print("Formatting applied!")
print("Done!")
