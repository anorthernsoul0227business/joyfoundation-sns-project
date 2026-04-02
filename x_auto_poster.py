#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X自動投稿システム - スプレッドシート連携版
スプレッドシートの投稿管理シートから予約投稿を自動実行する

使い方:
  python3 x_auto_poster.py          # 予約済み投稿を実行
  python3 x_auto_poster.py --dry    # ドライラン（実際には投稿しない）
  python3 x_auto_poster.py --list   # 予約済み一覧を表示
  python3 x_auto_poster.py --post 2 # Row 2を即時投稿
"""

import os
import sys
import io
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import gspread
import requests
from requests_oauthlib import OAuth1

# ログ設定
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'x_auto_poster.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 環境変数読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 定数
SPREADSHEET_ID = '1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM'
SHEET_NAME = 'X投稿v2'

# 列マッピング（0-indexed）
COL_DAY = 0          # A: Day
COL_TYPE = 1         # B: 投稿タイプ
COL_TEXT = 2         # C: 投稿テキスト
COL_IMG_PREVIEW = 3  # D: 画像（プレビュー）
COL_IMG_LINK = 4     # E: 画像リンク
COL_IMG2_PREVIEW = 5 # F: 画像2
COL_IMG2_LINK = 6    # G: 画像リンク2
COL_IMG3_PREVIEW = 7 # H: 画像3
COL_IMG3_LINK = 8    # I: 画像リンク3
COL_REPLY = 9        # J: リプ投稿
COL_COUNT = 10       # K: Xカウント
COL_TIME = 11        # L: 投稿時間
COL_STATUS = 12      # M: ステータス
COL_CONFIRM = 13     # N: 確認
COL_MEMO = 14        # O: メモ

# ステータス値
STATUS_SCHEDULED = '投稿予約'
STATUS_POSTED = '投稿済み'
STATUS_FAILED = '投稿失敗'


def get_x_auth():
    """X API OAuth1認証を取得"""
    return OAuth1(
        os.getenv('X_CONSUMER_KEY'),
        os.getenv('X_CONSUMER_SECRET'),
        os.getenv('X_ACCESS_TOKEN'),
        os.getenv('X_ACCESS_TOKEN_SECRET')
    )


def get_sheet():
    """スプレッドシートのX投稿v2シートを取得"""
    gc = gspread.service_account()
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(SHEET_NAME)


def upload_image_to_x(image_url, auth):
    """Google Drive画像をダウンロードしてX APIにアップロード"""
    try:
        # Drive URLからファイルIDを抽出
        if 'drive.google.com' in image_url:
            if '/d/' in image_url:
                file_id = image_url.split('/d/')[1].split('/')[0].split('?')[0]
            else:
                logger.warning(f"Drive URLからファイルIDを抽出できません: {image_url}")
                return None
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        else:
            download_url = image_url

        # 画像ダウンロード
        resp = requests.get(download_url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"画像ダウンロード失敗 ({resp.status_code}): {image_url}")
            return None

        # X API v1.1で画像アップロード
        upload_resp = requests.post(
            'https://upload.twitter.com/1.1/media/upload.json',
            auth=auth,
            files={'media': ('image.jpg', io.BytesIO(resp.content), 'image/jpeg')}
        )
        if upload_resp.status_code in (200, 201):
            media_id = upload_resp.json()['media_id_string']
            logger.info(f"画像アップロード成功: media_id={media_id}")
            return media_id
        else:
            logger.warning(f"画像アップロード失敗 ({upload_resp.status_code}): {upload_resp.text}")
            return None

    except Exception as e:
        logger.error(f"画像処理エラー: {e}")
        return None


def post_tweet(text, image_urls=None, auth=None):
    """ツイートを投稿（画像付き対応）"""
    if auth is None:
        auth = get_x_auth()

    media_ids = []
    if image_urls:
        for url in image_urls:
            if url and url.strip():
                media_id = upload_image_to_x(url.strip(), auth)
                if media_id:
                    media_ids.append(media_id)

    # v2 APIで投稿
    payload = {'text': text}
    if media_ids:
        payload['media'] = {'media_ids': media_ids}

    resp = requests.post(
        'https://api.twitter.com/2/tweets',
        auth=auth,
        json=payload
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        tweet_id = data['data']['id']
        logger.info(f"投稿成功! Tweet ID: {tweet_id} (画像{len(media_ids)}枚)")
        return tweet_id
    else:
        logger.error(f"投稿失敗 ({resp.status_code}): {resp.text}")
        return None


def get_scheduled_posts(ws):
    """予約済みで投稿時間が過ぎている投稿を取得"""
    all_data = ws.get_all_values()
    now = datetime.now()
    posts = []

    for row_idx, row in enumerate(all_data[1:], start=2):  # ヘッダーを除く
        if len(row) <= COL_STATUS:
            continue

        status = row[COL_STATUS].strip()
        if status != STATUS_SCHEDULED:
            continue

        # 投稿時間チェック
        post_time_str = row[COL_TIME].strip() if len(row) > COL_TIME else ''
        if post_time_str:
            try:
                # "YYYY-MM-DD HH:MM" または "HH:MM" 形式に対応
                if len(post_time_str) > 5:
                    post_time = datetime.strptime(post_time_str, '%Y-%m-%d %H:%M')
                else:
                    # 時間のみの場合は今日の日付を付与
                    today = now.strftime('%Y-%m-%d')
                    post_time = datetime.strptime(f"{today} {post_time_str}", '%Y-%m-%d %H:%M')

                if post_time > now:
                    continue  # まだ時間になっていない
            except ValueError:
                logger.warning(f"Row {row_idx}: 投稿時間の形式が不正: '{post_time_str}'")
                continue

        # 画像リンクを収集
        image_urls = []
        for col in [COL_IMG_LINK, COL_IMG2_LINK, COL_IMG3_LINK]:
            if len(row) > col and row[col].strip():
                image_urls.append(row[col].strip())

        posts.append({
            'row': row_idx,
            'day': row[COL_DAY],
            'type': row[COL_TYPE],
            'text': row[COL_TEXT],
            'image_urls': image_urls,
            'post_time': post_time_str,
        })

    return posts


def run_scheduled(dry_run=False):
    """予約投稿を実行"""
    logger.info("=" * 50)
    logger.info(f"X自動投稿チェック開始 {'(ドライラン)' if dry_run else ''}")

    ws = get_sheet()
    posts = get_scheduled_posts(ws)

    if not posts:
        logger.info("投稿すべき予約はありません")
        return

    logger.info(f"{len(posts)}件の投稿を実行します")
    auth = get_x_auth()

    for post in posts:
        logger.info(f"Row {post['row']}: {post['day']} - {post['text'][:50]}...")

        if dry_run:
            logger.info(f"  [ドライラン] スキップ (画像{len(post['image_urls'])}枚)")
            continue

        tweet_id = post_tweet(post['text'], post['image_urls'], auth)

        if tweet_id:
            # ステータスを「投稿済み」に更新
            ws.update_cell(post['row'], COL_STATUS + 1, STATUS_POSTED)
            # メモにツイートIDと投稿日時を記録
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            memo = f"投稿済 {timestamp} ID:{tweet_id}"
            ws.update_cell(post['row'], COL_MEMO + 1, memo)
            logger.info(f"  ステータス更新完了")
        else:
            ws.update_cell(post['row'], COL_STATUS + 1, STATUS_FAILED)
            logger.error(f"  投稿失敗 - ステータスを「投稿失敗」に更新")

        # レート制限対策
        time.sleep(3)

    logger.info("自動投稿チェック完了")


def list_scheduled():
    """予約済み一覧を表示"""
    ws = get_sheet()
    all_data = ws.get_all_values()

    print("\n=== X投稿v2 予約状況 ===\n")
    for row_idx, row in enumerate(all_data[1:], start=2):
        if len(row) <= COL_STATUS:
            continue
        status = row[COL_STATUS].strip() if row[COL_STATUS] else '-'
        day = row[COL_DAY] if row[COL_DAY] else ''
        post_time = row[COL_TIME] if len(row) > COL_TIME and row[COL_TIME] else '未設定'
        text_preview = row[COL_TEXT][:40] if row[COL_TEXT] else ''
        img_count = sum(1 for c in [COL_IMG_LINK, COL_IMG2_LINK, COL_IMG3_LINK]
                       if len(row) > c and row[c].strip())

        icon = {'投稿予約': '🕐', '投稿済み': '✅', '投稿失敗': '❌'}.get(status, '📝')
        print(f"  {icon} Row{row_idx:2d} | {day:20s} | {post_time:16s} | 画像{img_count} | {status:6s} | {text_preview}")

    print()


def post_single(row_num):
    """指定行を即時投稿"""
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
    print(f"Day: {row[COL_DAY]}")
    print(f"テキスト ({len(text)}文字):")
    print(text[:200])
    print(f"画像: {len(image_urls)}枚")

    confirm = input("\nこの投稿を公開しますか？ (y/N): ")
    if confirm.lower() != 'y':
        print("キャンセルしました")
        return

    auth = get_x_auth()
    tweet_id = post_tweet(text, image_urls, auth)

    if tweet_id:
        ws.update_cell(row_num, COL_STATUS + 1, STATUS_POSTED)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        ws.update_cell(row_num, COL_MEMO + 1, f"投稿済 {timestamp} ID:{tweet_id}")
        print(f"\n✅ 投稿成功! https://x.com/SFH_Science/status/{tweet_id}")
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
            post_single(int(sys.argv[idx + 1]))
        else:
            print("行番号を指定してください: --post 2")
    else:
        run_scheduled()
