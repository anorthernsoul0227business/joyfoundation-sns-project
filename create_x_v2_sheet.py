#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X投稿v2シートをGoogle Sheetsに追加"""

import gspread

gc = gspread.service_account()
sh = gc.open_by_key("1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")

try:
    ws = sh.add_worksheet(title="X投稿v2", rows=30, cols=10)
    print("Sheet created")
except:
    ws = sh.worksheet("X投稿v2")
    ws.clear()
    print("Sheet cleared")

header = ['Day', '投稿タイプ', '投稿テキスト', 'Xカウント', 'メディア', '投稿時間', 'ステータス', '確認', 'メモ']
rows = [header]

rows.append([
    'Day1',
    '豆知識型',
    '1/fゆらぎ、知っていますか？\n\n波の音、焚き火、心臓の鼓動──\n自然界の心地いいものに共通するリズム\n\n規則的すぎず、ランダムすぎない\nちょうどいい揺れ\n\n美空ひばりや宇多田ヒカルの声にも\n含まれていると言われています\n\n私たちは25年間\nこのゆらぎを科学的に研究しています\n\n#1fゆらぎ #自然音',
    '276/280',
    '波形画像 or 短尺動画',
    '20:00-22:00',
    '下書き',
    '',
    '最もバズりやすいパターン。1/fゆらぎ×有名人の組み合わせ'
])

rows.append([
    'Day2',
    '呼びかけ型',
    '今夜、眠れない人へ\n\nスピーカーから\n小さな音量で自然音を流してみてください\n\nイヤホンじゃなくて、スピーカー\n音量は「かすかに聞こえる」くらい\n\n体は耳だけでなく\n全身で音を感じています\n\n#自然音 #睡眠 #眠れない夜に',
    '208/280',
    '15-30秒の自然音動画（波の音など）',
    '21:00-23:00',
    '下書き',
    '',
    '夜投稿が効果的。動画付きでリーチ増'
])

rows.append([
    'Day3',
    '豆知識型',
    '人の体の約70%は水分\n\n音は振動\n水中では空気の約4倍の速さで伝わる\n\nつまり体全体が「耳」なんです\n\nだからライブで体が震える\nお寺の鐘の音が体に響く\n\nどんな音を日常的に浴びるか\n意外と大事かもしれません\n\n#音の振動 #自然音 #セルフケア',
    '226/280',
    '水の波紋 or 音の振動の映像',
    '20:00-22:00',
    '下書き',
    '',
    '身近な体験に紐づけて共感を得る'
])

rows.append([
    'Day4',
    '体験共有型',
    '毎月、整形外科で\n「音」の無料体験会をやっています\n\n「えっ、整形外科で音？」\n\nそう思いますよね\n\n田園調布の長田整形外科は\n予防医療として音に注目\n\n参加された方の声\n「気づいたら眠ってた」\n「肩の力が抜けた」\n\n予約不要・無料です\n\n#KITAサウンドヒーリング #予防医療',
    '257/280',
    'ここちよい音の日の写真',
    '20:00-22:00',
    '下書き',
    '',
    '意外性で興味を引く。体験者の声が効果的'
])

rows.append([
    'Day5',
    '用途提示型',
    '自然音の使い分け\n\n🌊 波の音 → リラックスしたい時\n🌿 川の音 → 集中したい時\n🐦 鳥の声 → 朝の目覚めに\n🌧 雨音 → 眠りたい時\n\n正解はありません\nあなたが心地いいと感じるものを\n\nまずは今夜、寝る前に5分\n試してみませんか？\n\n#自然音 #リラックス #睡眠',
    '238/280',
    '自然の風景画像（4分割）',
    '20:00-22:00',
    '下書き',
    '',
    '絵文字リストで視認性UP。保存されやすい'
])

ws.update(rows, 'A1')
print(f"Wrote {len(rows)-1} rows")

# Format header (dark blue)
ws.format('A1:I1', {
    'backgroundColor': {'red': 0.1, 'green': 0.1, 'blue': 0.5},
    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True}
})

requests = []
sheet_id = ws.id
widths = [50, 90, 400, 70, 180, 90, 70, 60, 250]
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
        'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 2, 'endColumnIndex': 3},
        'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
        'fields': 'userEnteredFormat.wrapStrategy'
    }
})
requests.append({
    'repeatCell': {
        'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'startColumnIndex': 8, 'endColumnIndex': 9},
        'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP'}},
        'fields': 'userEnteredFormat.wrapStrategy'
    }
})
sh.batch_update({'requests': requests})
print("Formatting applied!")
print("Done!")
