#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像をGoogle Driveにアップロードし、シートの画像列にリンク"""

import os
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Auth
SA_FILE = os.path.expanduser('~/.config/gspread/service_account.json')
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)
gc = gspread.service_account()

SHEET_ID = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("X投稿v2")

# Create folder in Drive
folder_meta = {
    'name': 'SNS投稿画像',
    'mimeType': 'application/vnd.google-apps.folder'
}
folder = drive.files().create(body=folder_meta, fields='id').execute()
folder_id = folder['id']
print(f"Created folder: {folder_id}")

# Make folder accessible
drive.permissions().create(
    fileId=folder_id,
    body={'type': 'anyone', 'role': 'reader'}
).execute()

BASE = "/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/カルーセル画像素材"

# Map: row title keyword -> image file path
image_map = {
    # Day4 events (体験共有型 - ここちよい音の日)
    'Day4': os.path.join(BASE, "Day4_Day5", "Day4④田園調布長田整形外科ここちよい音の日_50752257.JPG"),
    # Event: ここちよい音の日 4/18
    'ここちよい音の日 4/18': os.path.join(BASE, "Day4_Day5", "Day5 田園調布長田整形外科①2025.2.15 IMG_0520.jpg"),
    # Event: ここちよい音の日 5/16
    'ここちよい音の日 5/16': os.path.join(BASE, "Day4_Day5", "Day5 田園調布長田整形2024.5.18　ここちよい音の日-2.jpg"),
    # Event: スターライト さいたま 4/12
    'スターライト さいたま 4/12': os.path.join(BASE, "Day4_Day5", "Day4 ④さいたま市宇宙劇場ドーム内「2023スターライトヒーリング」.JPG"),
    # Event: スターライト さいたま 5月
    'スターライト さいたま 5月': os.path.join(BASE, "Day4_Day5", "Day4 ④さいたま市宇宙劇場ドーム内「2023スターライトヒーリング」.JPG"),
    # Event: スターライト 仙台 4月
    'スターライト 仙台 4月': os.path.join(BASE, "Day4_Day5", "Day4 ④仙台市天文台プラネタリウムIMG_0901.JPG"),
    # Event: スターライト 仙台 5月
    'スターライト 仙台 5月': os.path.join(BASE, "Day4_Day5", "Day4 ④仙台市天文台プラネタリウムIMG_0901.JPG"),
    # Event: 体験WS 自由が丘 4/16
    '体験WS 自由が丘 4/16': os.path.join(BASE, "Day4_Day5", "Day4 ④I自由が丘lab MG_0677 コピー②.JPG"),
    # Event: 体験WS 自由が丘 5/14
    '体験WS 自由が丘 5/14': os.path.join(BASE, "Day4_Day5", "Day4 ④I自由が丘lab MG_0677 コピー②.JPG"),
    # Event: 太陽食品コラボ
    '太陽食品コラボ 4/2-4': os.path.join(BASE, "Day4_Day5", "Day5 田園調布長田整形外科ここちよい音の日トークe_50438401.JPG"),
    # Day2 学会
    '認定研修 第90期': os.path.join(BASE, "Day2_Day4", "Day2 ③第78回日本温泉気候物理医学会.png"),
    '認定研修 第91期': os.path.join(BASE, "Day2_Day4", "Day2 ③第31回日本催眠学会.JPG"),
    # Day4 体感音響
    'オンライン体験講座 4月': os.path.join(BASE, "Day2_Day4", "Day4 ② 手のひらサイズの体感音響クッションで　肩と腰コース.jpg"),
}

# Upload images and get URLs
uploaded = {}
for key, filepath in image_map.items():
    if not os.path.exists(filepath):
        print(f"SKIP (not found): {key} -> {filepath}")
        continue

    filename = os.path.basename(filepath)
    ext = filename.rsplit('.', 1)[-1].lower()
    mime = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png', 'webp': 'image/webp'
    }.get(ext, 'image/jpeg')

    file_meta = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(filepath, mimetype=mime)
    f = drive.files().create(body=file_meta, media_body=media, fields='id').execute()
    file_id = f['id']

    # Make publicly accessible
    drive.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    url = f"https://drive.google.com/uc?id={file_id}"
    uploaded[key] = url
    print(f"Uploaded: {key} -> {file_id}")

# Update sheet - column D (index 4) is "画像/動画"
all_data = ws.get_all_values()
updates = []
for i, row in enumerate(all_data[1:], 2):  # start from row 2
    day_title = row[0]  # Day column
    for key, url in uploaded.items():
        if key in day_title:
            # Use IMAGE formula to show thumbnail
            formula = f'=IMAGE("{url}", 1)'
            updates.append({'range': f'D{i}', 'values': [[formula]]})
            print(f"Row {i} ({day_title}): linked to {key}")
            break

if updates:
    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print(f"\nUpdated {len(updates)} image cells")
else:
    print("No updates made")

print("Done!")
