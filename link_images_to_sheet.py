#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Drive上の画像をシートのIMAGE関数でリンク"""

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

SA_FILE = os.path.expanduser('~/.config/gspread/service_account.json')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

# Folder IDs from Google Drive URLs
FOLDER_DAY2_4 = "1NgZmb2HR5S27Jc6NeFa-pLc0yRJUFC78"

# List files in Day2_Day4
def list_files(folder_id):
    results = drive.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'image/'",
        fields="files(id, name)"
    ).execute()
    return results.get('files', [])

print("=== Day2_Day4 ===")
files_d2 = list_files(FOLDER_DAY2_4)
for f in files_d2:
    print(f"  {f['name']} -> {f['id']}")

# Now try to find Day4_Day5 folder
# Search for it in the user's drive (public)
results = drive.files().list(
    q="name='Day4_Day5' and mimeType='application/vnd.google-apps.folder'",
    fields="files(id, name)"
).execute()
folders = results.get('files', [])
if folders:
    FOLDER_DAY4_5 = folders[0]['id']
    print(f"\n=== Day4_Day5 ({FOLDER_DAY4_5}) ===")
    files_d4 = list_files(FOLDER_DAY4_5)
    for f in files_d4:
        print(f"  {f['name']} -> {f['id']}")
else:
    print("\nDay4_Day5 folder not found via API. Trying direct listing...")
    files_d4 = []

all_files = {}
for f in files_d2 + files_d4:
    all_files[f['name']] = f['id']

print(f"\nTotal: {len(all_files)} files")

# Map files to sheet rows
image_assignments = {
    'Day4': '田園調布長田整形外科ここちよい音の日',
    'ここちよい音の日 4/18': '田園調布長田整形外科',
    'ここちよい音の日 5/16': 'ここちよい音の日',
    'スターライト さいたま 4/12': 'さいたま市宇宙劇場',
    'スターライト さいたま 5月': 'さいたま市宇宙劇場',
    'スターライト 仙台 4月': '仙台市天文台',
    'スターライト 仙台 5月': '仙台市天文台',
    '体験WS 自由が丘 4/16': '自由が丘lab',
    '体験WS 自由が丘 5/14': '自由が丘lab',
    '認定研修 第90期': '温泉気候物理医学会',
    '認定研修 第91期': '催眠学会',
    'オンライン体験講座': '体感音響クッション',
    '太陽食品コラボ': 'クルーズ',
}

# Find matching files
matched = {}
for row_key, search_term in image_assignments.items():
    for fname, fid in all_files.items():
        if search_term in fname:
            matched[row_key] = (fname, fid)
            break

print(f"\nMatched {len(matched)} images to rows:")
for k, (fname, fid) in matched.items():
    print(f"  {k} -> {fname}")

# Update Google Sheet
gc = gspread.service_account()
sh = gc.open_by_key("1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM")
ws = sh.worksheet("X投稿v2")

all_data = ws.get_all_values()
updates = []
for i, row in enumerate(all_data[1:], 2):
    day_title = row[0]
    for row_key, (fname, fid) in matched.items():
        if row_key in day_title:
            url = f"https://drive.google.com/uc?export=view&id={fid}"
            formula = f'=IMAGE("{url}")'
            updates.append({'range': f'D{i}', 'values': [[formula]]})
            print(f"Row {i} ({day_title}): {fname}")
            break

if updates:
    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print(f"\nUpdated {len(updates)} cells with images")
else:
    print("\nNo updates - check file matching")

print("Done!")
