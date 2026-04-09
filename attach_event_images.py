#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全イベント記事に画像を添付する。
公式ポスター/チラシはPDF→PNG変換→R2アップロード。
Drive上の既存画像はそのままIMAGE関数でリンク。
"""

import os
import subprocess
import gspread
import boto3
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv('/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/.env')

SPREADSHEET_ID = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
PROJECT_DIR = "/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project"

# R2 設定
R2_ENDPOINT = f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"
R2_BUCKET = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL')

s3 = boto3.client('s3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    region_name='auto'
)

# Google API
SA_FILE = os.path.expanduser('~/.config/gspread/service_account.json')
gc = gspread.service_account()
sh = gc.open_by_key(SPREADSHEET_ID)


def pdf_to_png(pdf_path, output_path, dpi=200):
    """PDFの1ページ目をPNGに変換"""
    base = output_path.rsplit('.', 1)[0]
    subprocess.run([
        'pdftoppm', '-png', '-f', '1', '-l', '1', '-r', str(dpi),
        pdf_path, base
    ], check=True)
    # pdftoppm outputs base-1.png
    generated = f"{base}-1.png"
    if os.path.exists(generated):
        os.rename(generated, output_path)
    return output_path


def upload_to_r2(local_path, r2_key):
    """R2にアップロードして公開URLを返す"""
    content_type = 'image/png' if r2_key.endswith('.png') else 'image/jpeg'
    s3.upload_file(local_path, R2_BUCKET, r2_key,
                   ExtraArgs={'ContentType': content_type})
    url = f"{R2_PUBLIC_URL}/{r2_key}"
    print(f"  R2: {r2_key} -> {url}")
    return url


def drive_image_url(file_id):
    """Google DriveのIMAGE関数用URL"""
    return f"https://drive.google.com/uc?export=view&id={file_id}"


# ============================================================
# Step 1: ローカルPDFを画像化してR2にアップロード
# ============================================================
print("=== PDF → PNG → R2 アップロード ===")

r2_images = {}
pdfs_to_convert = [
    ('カンガルーカップ2026_公式ポスター',
     f'{PROJECT_DIR}/イベント資料/カンガルーカップ2026/カンガルーカップ2026_公式ポスター.pdf',
     'event-images/kangaroo_cup_2026_poster.png'),
    ('スターライト_さいたま_チラシ',
     f'{PROJECT_DIR}/イベント資料/スターライトヒーリング_20260412/★さいたま市star_light_healing_2025.jpg',
     None),  # Already an image
    ('スターライト_チラシ裏',
     f'{PROJECT_DIR}/イベント資料/スターライトヒーリング_20260412/★star_light_healing_2025_v4_fix_ura.jpg',
     None),  # Already an image
    ('仙台スターライト_チラシ',
     f'{PROJECT_DIR}/イベント資料/スターライトヒーリング_20260412/★P29仙台star_light_healing_2026_sen_A4_v2.pdf',
     'event-images/starlight_sendai_2026_flyer.png'),
    ('太陽食品_チラシ表',
     f'{PROJECT_DIR}/イベント資料/ここちよい音の日_20260402-04/★チラシ：太陽食品＆SH協会のコラボ企画 『ここちよい音の日』2026.4.2-4.pdf',
     'event-images/taiyo_foods_collab_flyer.png'),
]

tmp_dir = '/tmp/event_images'
os.makedirs(tmp_dir, exist_ok=True)

for name, src_path, r2_key in pdfs_to_convert:
    if not os.path.exists(src_path):
        print(f"  SKIP: {name} (file not found)")
        continue

    if r2_key is None:
        # Already an image, upload directly
        ext = os.path.splitext(src_path)[1].lower()
        r2_key = f"event-images/{name.lower().replace(' ', '_')}{ext}"
        url = upload_to_r2(src_path, r2_key)
        r2_images[name] = url
    elif src_path.endswith('.pdf'):
        png_path = f"{tmp_dir}/{os.path.basename(r2_key)}"
        print(f"  Converting: {name}")
        pdf_to_png(src_path, png_path)
        url = upload_to_r2(png_path, r2_key)
        r2_images[name] = url
    else:
        url = upload_to_r2(src_path, r2_key)
        r2_images[name] = url

# カンガルーカップの写真もR2にアップ
kc_photos = [
    f'{PROJECT_DIR}/イベント資料/カンガルーカップ2026/2025.5.1 Kangaroo Cup2025.jpg',
    f'{PROJECT_DIR}/イベント資料/カンガルーカップ2026/IMG_0744.jpg',
]
for photo in kc_photos:
    if os.path.exists(photo):
        fn = os.path.basename(photo).replace(' ', '_').replace('　', '_')
        r2_key = f"event-images/kangaroo_{fn}"
        url = upload_to_r2(photo, r2_key)

print(f"\nR2アップロード完了: {len(r2_images)}件")
for k, v in r2_images.items():
    print(f"  {k}: {v}")

# ============================================================
# Step 2: イベント→画像マッピング
# ============================================================
print("\n=== 画像マッピング ===")

# Drive画像のID
DRIVE_IMAGES = {
    'さいたま宇宙劇場': '1giG_3QblPxrdSPCm-K9hWgHaiNNY_GKr',  # Day4 さいたま市宇宙劇場ドーム内
    '仙台天文台': '1Ih6c3tAq2YcZ5HO_pq6V112Yj6QUb8An',  # Day4 仙台市天文台プラネタリウム
    '自由が丘lab': '1l6YWd2h0281Sx4vxSvy9W6jl8vJNcKPm',  # Day4 自由が丘lab
    'ここちよい音の日': '1RuDMGx2QByEv1uERLXyVAt_MqN1krVJ1',  # Day5 ここちよい音の日
    '体感音響クッション': '1sXsfz_q8sZ0UfM-FSEcBEbSLlryCuYI_',  # 手のひらサイズの体感音響クッション
    '研修会_催眠学会': '1KkWfwGuzac7J_urRobBSVbYl-79ZEED4',  # 第31回日本催眠学会
    '研修会_温泉学会': '1YIRuckrS9yVxpWzarmxpirSjYfL5lDKB',  # 第78回日本温泉気候物理医学会
    'クルーズ': '1bVAdiPS837X3j6GLx_aSXFq2Y8T8g9nZ',  # Well-Bing Cruise
    'セラピスト研修': '1PrsoQghnjQ_laY8rH5ylN73Ys_Z0iPn5',  # 上体ケア
}

# IGイベント投稿のマッピング (No -> image URL)
# 公式ポスター/チラシを最優先
ig_image_map = {
    1:  drive_image_url(DRIVE_IMAGES['研修会_催眠学会']),      # ファシリテーター研修88期
    2:  r2_images.get('仙台スターライト_チラシ', ''),           # スターライト仙台 ★公式チラシ
    3:  r2_images.get('スターライト_さいたま_チラシ', ''),       # スターライトさいたま ★公式チラシ
    4:  drive_image_url(DRIVE_IMAGES['体感音響クッション']),     # オンライン体験講座(延期)
    5:  drive_image_url(DRIVE_IMAGES['自由が丘lab']),           # 体験WS自由が丘
    6:  drive_image_url(DRIVE_IMAGES['ここちよい音の日']),       # ここちよい音の日4月
    7:  drive_image_url(DRIVE_IMAGES['セラピスト研修']),        # セラピスト研修41期
    8:  r2_images.get('カンガルーカップ2026_公式ポスター', ''),  # カンガルーカップ ★公式ポスター
    9:  r2_images.get('スターライト_さいたま_チラシ', ''),       # スターライトさいたま5月
    10: drive_image_url(DRIVE_IMAGES['自由が丘lab']),           # 体験WS5月
    11: drive_image_url(DRIVE_IMAGES['ここちよい音の日']),       # ここちよい音の日5月
    12: drive_image_url(DRIVE_IMAGES['体感音響クッション']),     # オンラインWS5月
    13: '',  # 告知不要
    14: '',  # 告知不要
    15: r2_images.get('太陽食品_チラシ表', ''),                  # 太陽食品コラボ ★公式チラシ
    16: drive_image_url(DRIVE_IMAGES['研修会_催眠学会']),        # ファシリテーター研修89期
    17: r2_images.get('スターライト_さいたま_チラシ', ''),       # スターライトさいたま6月
    18: drive_image_url(DRIVE_IMAGES['自由が丘lab']),           # 体験WS6月
    19: drive_image_url(DRIVE_IMAGES['ここちよい音の日']),       # ここちよい音の日6月
    20: drive_image_url(DRIVE_IMAGES['体感音響クッション']),     # オンラインWS6月
    21: drive_image_url(DRIVE_IMAGES['研修会_温泉学会']),        # 抗加齢医学学会
    22: r2_images.get('スターライト_さいたま_チラシ', ''),       # スターライトさいたま7月
    23: drive_image_url(DRIVE_IMAGES['自由が丘lab']),           # 体験WS7月
    24: drive_image_url(DRIVE_IMAGES['ここちよい音の日']),       # ここちよい音の日7月
    25: drive_image_url(DRIVE_IMAGES['体感音響クッション']),     # オンラインWS7月
}

# ============================================================
# Step 3: IGイベント投稿シートに画像リンクを設定
# ============================================================
print("\n=== IGイベント投稿 画像リンク設定 ===")
ig_ws = sh.worksheet('IGイベント投稿')
ig_data = ig_ws.get_all_values()
header = ig_data[0]

# 画像リンク列を特定
link_col_idx = header.index('画像リンク')
link_col_letter = chr(65 + link_col_idx) if link_col_idx < 26 else chr(64 + link_col_idx // 26) + chr(65 + link_col_idx % 26)

updates = []
for no, url in ig_image_map.items():
    if not url:
        continue
    # Noの値でrow検索
    for i, row in enumerate(ig_data[1:], 2):
        if str(row[0]).strip() == str(no):
            updates.append({'range': f'{link_col_letter}{i}', 'values': [[url]]})
            print(f"  No.{no} (row {i}): 画像リンク設定")
            break

if updates:
    ig_ws.batch_update(updates, value_input_option='USER_ENTERED')
    print(f"  {len(updates)}件更新完了")

# ============================================================
# Step 4: Xイベント投稿シートに画像リンクを設定
# ============================================================
print("\n=== Xイベント投稿 画像リンク設定 ===")
x_ws = sh.worksheet('Xイベント投稿')
x_data = x_ws.get_all_values()
x_header = x_data[0]
x_link_idx = x_header.index('画像リンク')
x_link_letter = chr(65 + x_link_idx) if x_link_idx < 26 else chr(64 + x_link_idx // 26) + chr(65 + x_link_idx % 26)

# Xイベント投稿のマッピング (イベント名キーワード → URL)
x_image_map = {
    'オンライン体験講座': drive_image_url(DRIVE_IMAGES['体感音響クッション']),
    'ここちよい音の日': drive_image_url(DRIVE_IMAGES['ここちよい音の日']),
    'スターライトヒーリング さいたま': r2_images.get('スターライト_さいたま_チラシ', ''),
    'スターライトヒーリング 仙台': r2_images.get('仙台スターライト_チラシ', ''),
    '体験WS 自由が丘': drive_image_url(DRIVE_IMAGES['自由が丘lab']),
    '認定研修 第89期': drive_image_url(DRIVE_IMAGES['研修会_催眠学会']),
    'カンガルーカップ': r2_images.get('カンガルーカップ2026_公式ポスター', ''),
    'オンラインWS 5月': drive_image_url(DRIVE_IMAGES['体感音響クッション']),
    '太陽食品コラボ': r2_images.get('太陽食品_チラシ表', ''),
    'オンラインWS 6月': drive_image_url(DRIVE_IMAGES['体感音響クッション']),
    '抗加齢医学学会': drive_image_url(DRIVE_IMAGES['研修会_温泉学会']),
    'オンラインWS 7月': drive_image_url(DRIVE_IMAGES['体感音響クッション']),
}

x_updates = []
for i, row in enumerate(x_data[1:], 2):
    event_name = row[0] if len(row) > 0 else ''
    for keyword, url in x_image_map.items():
        if keyword in event_name and url:
            x_updates.append({'range': f'{x_link_letter}{i}', 'values': [[url]]})
            print(f"  Row {i} ({event_name}): 画像リンク設定")
            break

if x_updates:
    x_ws.batch_update(x_updates, value_input_option='USER_ENTERED')
    print(f"  {len(x_updates)}件更新完了")

print("\n全完了!")
print(f"  IG: {len(updates)}件")
print(f"  X: {len(x_updates)}件")
