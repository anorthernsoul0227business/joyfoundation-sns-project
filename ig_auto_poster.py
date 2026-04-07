#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram自動投稿システム - スプレッドシート連携版
スプレッドシートのIG投稿キューシートから予約投稿を自動実行する

使い方:
  python3 ig_auto_poster.py          # 予約済み投稿を実行
  python3 ig_auto_poster.py --dry    # ドライラン（実際には投稿しない）
  python3 ig_auto_poster.py --list   # 予約済み一覧を表示
  python3 ig_auto_poster.py --post 2 # Row 2を即時投稿
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import gspread
import requests

# ログ設定
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'ig_auto_poster.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 環境変数読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 定数
SPREADSHEET_ID = '1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM'
SHEET_NAME = 'IG投稿キュー'
GRAPH_API_VERSION = 'v25.0'
GRAPH_API_BASE = f'https://graph.facebook.com/{GRAPH_API_VERSION}'

# 列マッピング（0-indexed）- IG投稿キューのシンプル構成
# A:投稿日時 B:キャプション C:画像1 D:画像リンク1 E:画像2 F:画像リンク2 G:画像3 H:画像リンク3 I:ステータス J:メモ
COL_TIME = 0         # A: 投稿日時
COL_TEXT = 1         # B: キャプション
COL_IMG_LINK = 3     # D: 画像リンク1
COL_IMG2_LINK = 5    # F: 画像リンク2
COL_IMG3_LINK = 7    # H: 画像リンク3
COL_STATUS = 8       # I: ステータス
COL_MEMO = 9         # J: メモ

# ステータス値
STATUS_SCHEDULED = '投稿予約'
STATUS_POSTED = '投稿済み'
STATUS_FAILED = '投稿失敗'


def get_ig_credentials():
    """IG API認証情報を取得"""
    token = os.getenv('IG_ACCESS_TOKEN')
    account_id = os.getenv('IG_BUSINESS_ACCOUNT_ID')
    if not token or not account_id:
        logger.error("IG_ACCESS_TOKEN または IG_BUSINESS_ACCOUNT_ID が未設定")
        return None, None
    return token, account_id


def get_sheet():
    """スプレッドシートのIG投稿キューシートを取得"""
    gc = gspread.service_account()
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(SHEET_NAME)


def drive_url_to_lh3(drive_url):
    """Google DriveのURLをlh3形式の公開URLに変換"""
    if not drive_url or 'drive.google.com' not in drive_url:
        return drive_url
    if '/d/' in drive_url:
        file_id = drive_url.split('/d/')[1].split('/')[0].split('?')[0]
    elif 'id=' in drive_url:
        file_id = drive_url.split('id=')[1].split('&')[0]
    else:
        return drive_url
    return f"https://lh3.googleusercontent.com/d/{file_id}"


def post_single_image(image_url, caption, token, account_id):
    """単画像投稿"""
    public_url = drive_url_to_lh3(image_url)
    logger.info(f"画像URL: {public_url[:80]}...")

    # Step 1: Container作成
    resp = requests.post(
        f"{GRAPH_API_BASE}/{account_id}/media",
        data={
            "image_url": public_url,
            "caption": caption,
            "access_token": token
        }
    )
    if resp.status_code != 200:
        logger.error(f"Container作成失敗: {resp.status_code} {resp.text}")
        return None

    container_id = resp.json()['id']
    logger.info(f"Container作成: {container_id}")

    # Step 2: ステータス待機
    for i in range(15):
        status_resp = requests.get(
            f"{GRAPH_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token}
        )
        status = status_resp.json().get('status_code')
        if status == 'FINISHED':
            break
        elif status == 'ERROR':
            logger.error("Container処理エラー")
            return None
        time.sleep(3)

    # Step 3: 公開
    pub_resp = requests.post(
        f"{GRAPH_API_BASE}/{account_id}/media_publish",
        data={"creation_id": container_id, "access_token": token}
    )
    if pub_resp.status_code == 200:
        post_id = pub_resp.json()['id']
        logger.info(f"投稿成功: {post_id}")
        return post_id

    logger.error(f"公開失敗: {pub_resp.status_code} {pub_resp.text}")
    return None


def post_carousel(image_urls, caption, token, account_id):
    """カルーセル投稿（複数画像）"""
    children_ids = []
    for url in image_urls:
        public_url = drive_url_to_lh3(url)
        resp = requests.post(
            f"{GRAPH_API_BASE}/{account_id}/media",
            data={
                "image_url": public_url,
                "is_carousel_item": True,
                "access_token": token
            }
        )
        if resp.status_code == 200:
            children_ids.append(resp.json()['id'])
            logger.info(f"カルーセルアイテム作成: {resp.json()['id']}")
        else:
            logger.warning(f"カルーセルアイテム失敗: {resp.status_code} {resp.text}")

    if not children_ids:
        return None

    # 各アイテムの処理完了を待機
    time.sleep(10)

    # カルーセルコンテナ作成
    carousel_resp = requests.post(
        f"{GRAPH_API_BASE}/{account_id}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ','.join(children_ids),
            "caption": caption,
            "access_token": token
        }
    )
    if carousel_resp.status_code != 200:
        logger.error(f"カルーセルContainer失敗: {carousel_resp.status_code} {carousel_resp.text}")
        return None

    carousel_id = carousel_resp.json()['id']

    # 処理完了待機
    for i in range(15):
        status_resp = requests.get(
            f"{GRAPH_API_BASE}/{carousel_id}",
            params={"fields": "status_code", "access_token": token}
        )
        status = status_resp.json().get('status_code')
        if status == 'FINISHED':
            break
        elif status == 'ERROR':
            logger.error("カルーセルContainer処理エラー")
            return None
        time.sleep(3)

    # 公開
    pub_resp = requests.post(
        f"{GRAPH_API_BASE}/{account_id}/media_publish",
        data={"creation_id": carousel_id, "access_token": token}
    )
    if pub_resp.status_code == 200:
        post_id = pub_resp.json()['id']
        logger.info(f"カルーセル投稿成功: {post_id} ({len(children_ids)}枚)")
        return post_id

    logger.error(f"カルーセル公開失敗: {pub_resp.status_code} {pub_resp.text}")
    return None


def get_scheduled_posts(ws):
    """予約済みで投稿時間が過ぎている投稿を取得"""
    all_data = ws.get_all_values()
    now = datetime.now()
    posts = []

    for row_idx, row in enumerate(all_data[1:], start=2):
        if len(row) <= COL_STATUS:
            continue

        status = row[COL_STATUS].strip()
        if status != STATUS_SCHEDULED:
            continue

        post_time_str = row[COL_TIME].strip() if len(row) > COL_TIME else ''
        if post_time_str:
            try:
                normalized = post_time_str.replace('/', '-')
                post_time = None
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%H:%M']:
                    try:
                        if fmt == '%H:%M':
                            today = now.strftime('%Y-%m-%d')
                            post_time = datetime.strptime(f"{today} {normalized}", f'%Y-%m-%d {fmt}')
                        else:
                            post_time = datetime.strptime(normalized, fmt)
                        break
                    except ValueError:
                        continue

                if post_time is None:
                    raise ValueError(f"未対応の形式: {post_time_str}")

                if post_time > now:
                    continue
                if (now - post_time) > timedelta(hours=24):
                    continue
            except ValueError:
                logger.warning(f"Row {row_idx}: 投稿時間の形式が不正: '{post_time_str}'")
                continue

        image_urls = []
        for col in [COL_IMG_LINK, COL_IMG2_LINK, COL_IMG3_LINK]:
            if len(row) > col and row[col].strip():
                image_urls.append(row[col].strip())

        posts.append({
            'row': row_idx,
            'text': row[COL_TEXT],
            'image_urls': image_urls,
            'post_time': post_time_str,
        })

    return posts


def run_scheduled(dry_run=False):
    """予約投稿を実行"""
    logger.info("=" * 50)
    logger.info(f"IG自動投稿チェック開始 {'(ドライラン)' if dry_run else ''}")

    token, account_id = get_ig_credentials()
    if not token:
        return

    ws = get_sheet()
    posts = get_scheduled_posts(ws)

    if not posts:
        logger.info("投稿すべき予約はありません")
        return

    logger.info(f"{len(posts)}件の投稿を実行します")

    for post in posts:
        logger.info(f"Row {post['row']}: {post['text'][:50]}...")

        if dry_run:
            logger.info(f"  [ドライラン] スキップ (画像{len(post['image_urls'])}枚)")
            continue

        if not post['image_urls']:
            logger.warning(f"  画像なし - スキップ")
            ws.update_cell(post['row'], COL_STATUS + 1, STATUS_FAILED)
            ws.update_cell(post['row'], COL_MEMO + 1, "エラー: 画像URLなし")
            continue

        # 画像数に応じて単画像 or カルーセル
        if len(post['image_urls']) == 1:
            post_id = post_single_image(post['image_urls'][0], post['text'], token, account_id)
        else:
            post_id = post_carousel(post['image_urls'], post['text'], token, account_id)

        if post_id:
            ws.update_cell(post['row'], COL_STATUS + 1, STATUS_POSTED)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            ws.update_cell(post['row'], COL_MEMO + 1, f"投稿済 {timestamp} ID:{post_id}")
            logger.info(f"  ステータス更新完了")
        else:
            ws.update_cell(post['row'], COL_STATUS + 1, STATUS_FAILED)
            ws.update_cell(post['row'], COL_MEMO + 1, f"投稿失敗 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            logger.error(f"  投稿失敗")

        time.sleep(5)

    logger.info("IG自動投稿チェック完了")


def list_scheduled():
    """予約済み一覧を表示"""
    ws = get_sheet()
    all_data = ws.get_all_values()

    print("\n=== IG投稿キュー 予約状況 ===\n")
    for row_idx, row in enumerate(all_data[1:], start=2):
        if len(row) <= COL_STATUS:
            continue
        status = row[COL_STATUS].strip() if row[COL_STATUS] else '-'
        post_time = row[COL_TIME] if len(row) > COL_TIME and row[COL_TIME] else '未設定'
        text_preview = row[COL_TEXT][:40] if row[COL_TEXT] else ''
        img_count = sum(1 for c in [COL_IMG_LINK, COL_IMG2_LINK, COL_IMG3_LINK]
                       if len(row) > c and row[c].strip())

        icon = {'投稿予約': '🕐', '投稿済み': '✅', '投稿失敗': '❌'}.get(status, '📝')
        print(f"  {icon} Row{row_idx:2d} | {post_time:16s} | 画像{img_count} | {status:6s} | {text_preview}")

    print()


def post_single_row(row_num):
    """指定行を即時投稿"""
    token, account_id = get_ig_credentials()
    if not token:
        return

    ws = get_sheet()
    row = ws.row_values(row_num)

    if not row or len(row) < COL_TEXT + 1:
        print(f"Row {row_num} にデータがありません")
        return

    text = row[COL_TEXT]
    image_urls = []
    for col in [COL_IMG_LINK, COL_IMG2_LINK, COL_IMG3_LINK]:
        if len(row) > col and row[col].strip():
            image_urls.append(row[col].strip())

    print(f"\n投稿内容 (Row {row_num}):")
    print(f"キャプション ({len(text)}文字):")
    print(text[:200])
    print(f"画像: {len(image_urls)}枚")

    confirm = input("\nこの投稿を公開しますか？ (y/N): ")
    if confirm.lower() != 'y':
        print("キャンセルしました")
        return

    if len(image_urls) == 1:
        post_id = post_single_image(image_urls[0], text, token, account_id)
    elif len(image_urls) > 1:
        post_id = post_carousel(image_urls, text, token, account_id)
    else:
        print("画像がありません")
        return

    if post_id:
        ws.update_cell(row_num, COL_STATUS + 1, STATUS_POSTED)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        ws.update_cell(row_num, COL_MEMO + 1, f"投稿済 {timestamp} ID:{post_id}")
        print(f"\n✅ 投稿成功! ID: {post_id}")
    else:
        print("\n❌ 投稿失敗")


if __name__ == '__main__':
    if '--dry' in sys.argv:
        run_scheduled(dry_run=True)
    elif '--list' in sys.argv:
        list_scheduled()
    elif '--post' in sys.argv:
        idx = sys.argv.index('--post')
        if idx + 1 < len(sys.argv):
            post_single_row(int(sys.argv[idx + 1]))
        else:
            print("行番号を指定してください: --post 2")
    else:
        run_scheduled()
