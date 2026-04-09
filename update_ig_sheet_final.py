#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instagramシートを最終修正版キャプションで更新し、画像を追加"""

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

SA_FILE = os.path.expanduser('~/.config/gspread/service_account.json')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

# Get all Drive files
FOLDER_DAY2_4 = "1NgZmb2HR5S27Jc6NeFa-pLc0yRJUFC78"
FOLDER_DAY4_5 = "1KbTcd6TGHgd-HqVxQ42XRCZLL0d2OSw5"

all_files = {}
for fid in [FOLDER_DAY2_4, FOLDER_DAY4_5]:
    results = drive.files().list(
        q=f"'{fid}' in parents and mimeType contains 'image/'",
        fields="files(id, name)"
    ).execute()
    for f in results.get('files', []):
        all_files[f['name']] = f['id']

print(f"Total Drive files: {len(all_files)}")

# Image mapping for Instagram carousel Days
# Day2③ 学会写真, Day2④ クルーズ/企業写真
# Day4② 体感音響クッション, Day4③ マイアミ, Day4④ 自由が丘lab/プラネタリウム/ここちよい音の日
# Day5 長田整形外科写真
ig_image_map = {
    2: '温泉気候物理医学会',    # Day2: 学会発表写真が代表
    4: '体感音響クッション',      # Day4: 体感音響クッション
    5: 'IMG_0520',              # Day5: 長田整形外科
}

gc = gspread.service_account()
sh = gc.open_by_key("1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")
ws = sh.worksheet("Instagram")

# First, update the captions to match final corrected version
# Day2③ "体験出展、研究発表" added
day2_caption = '【サウンドヒーリングって怪しくない？】\nそう思った方にこそ読んでほしい。\n\n━━━━━━━━━━━━━━━\n\n「音で癒し」と聞くと\nちょっと構えてしまう方もいるかもしれません。\n\nでも、川の音を聴いてホッとしたり\n雨音で眠くなったり──\nそれも立派なサウンドヒーリングです。\n\n━━━━━━━━━━━━━━━\n\n私たちは25年間、学会での体験出展、研究発表や\n企業・医療機関への導入を通じて\n音の可能性を探求してきました。\n\n━━━━━━━━━━━━━━━\n▼ まずは無料体験会へ\n\n#KITAサウンドヒーリング #サウンドヒーリングとは #自然音 #科学的根拠 #学会発表 #25年の実績 #怪しくない #音の力 #セルフケア #ウェルビーイング #心と体 #リラックス'

# Day3 "収録家の中田悟は10年以上" + "代表喜田圭一郎の30年以上の研究と制作の経験"
day3_caption = '【YouTubeの自然音BGMと何が違う？】\n\n━━━━━━━━━━━━━━━\n\n違いは「収録の仕方」にあります。\n\n収録家の中田悟は\n10年以上にわたり世界各地で自然音を収録してきました。\n\nただマイクを置くのではなく\nその場所の空気感ごとまるごと頂いてくる。\n\n収録する時の「心」も大切にしています。\n音源のクオリティは収録する人の意識で変わる──\n代表喜田圭一郎の30年以上の研究と制作の経験から確信していることです。\n\n━━━━━━━━━━━━━━━\n▼ 体験イベントはプロフィールから\n\n#KITAサウンドヒーリング #自然音 #自然音BGM #ハワイ #屋久島 #沖縄 #白神山地 #音のある暮らし #収録 #こだわり #リラックス #癒しの音'

# Day5⑤ "毎月１回土曜日"
day5_caption = '【なぜ整形外科で「音」の体験会？】\n\n━━━━━━━━━━━━━━━\n\n長田整形外科の長田夏哉院長は\n「病気にならない体をつくる」予防医療に取り組んでいます。\n\n「ここちよい音の日」は予約不要・参加無料。\n📅毎月１回土曜日\n📍田園調布・長田整形外科\n\n━━━━━━━━━━━━━━━\n▼ 詳しくはプロフィールから\n\n#KITAサウンドヒーリング #ここちよい音の日 #長田整形外科 #田園調布 #無料体験 #予防医療 #整形外科 #毎月開催 #予約不要 #セルフケア #自然音 #体感音響'

# Update captions (column D = index 4)
ws.update_cell(3, 4, day2_caption)  # Row 3 = Day2
ws.update_cell(4, 4, day3_caption)  # Row 4 = Day3
ws.update_cell(6, 4, day5_caption)  # Row 6 = Day5
print("Captions updated to final version")

# Now add image column - need to check if column exists
header = ws.row_values(1)
print(f"Current columns: {header}")

# Column F = "画像メモ" - let's use this for the IMAGE formula
# Find image matches and update
updates = []
for row_num, search_term in ig_image_map.items():
    sheet_row = row_num + 1  # +1 for header
    for fname, fid in all_files.items():
        if search_term in fname:
            url = f"https://drive.google.com/uc?export=view&id={fid}"
            formula = f'=IMAGE("{url}")'
            updates.append({'range': f'F{sheet_row}', 'values': [[formula]]})
            print(f"Row {sheet_row} (Day{row_num}): {fname}")
            break

# Also add all Day5 event images for reference
day5_images = []
for fname, fid in all_files.items():
    if 'Day5' in fname or ('Day4' in fname and '田園調布' in fname):
        day5_images.append(f"{fname}")

# Add Day2④ images (cruise/corporate)
day2_event_images = []
for fname, fid in all_files.items():
    if 'Day2 ④' in fname:
        url = f"https://drive.google.com/uc?export=view&id={fid}"
        day2_event_images.append((fname, url))

# Day2④ enterprise/medical image for slide 4
for fname, fid in all_files.items():
    if 'Cruise' in fname and 'SH体験' in fname:
        url = f"https://drive.google.com/uc?export=view&id={fid}"
        # Add as additional image note for Day2
        current_memo = ws.cell(3, 10).value or ''
        ws.update_cell(3, 10, f"④候補: {fname}\n{current_memo}")
        print(f"Day2 ④ memo: {fname}")
        break

# Day4③ マイアミ
for fname, fid in all_files.items():
    if 'マイアミ' in fname:
        url = f"https://drive.google.com/uc?export=view&id={fid}"
        current = ws.cell(5, 10).value or ''
        ws.update_cell(5, 10, f"③候補: {fname}\n{current}")
        print(f"Day4 ③ memo: {fname}")
        break

# Day4④ multiple venue images
day4_venues = []
for fname, fid in all_files.items():
    if 'Day4 ④' in fname or ('Day4④' in fname):
        day4_venues.append(fname)
if day4_venues:
    current = ws.cell(5, 10).value or ''
    ws.update_cell(5, 10, f"④候補: {', '.join(day4_venues)}\n{current}")
    print(f"Day4 ④ venues: {day4_venues}")

if updates:
    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print(f"\nUpdated {len(updates)} image cells")

print("Done!")
