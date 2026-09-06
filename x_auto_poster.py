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
from typing import Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import gspread
import requests
from requests_oauthlib import OAuth1

from notifier import build_default_notifier

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
SHEET_NAME = 'X投稿キュー'

# 列マッピング（0-indexed）- X投稿キューのシンプル構成
# A:投稿日時 B:投稿テキスト C:画像1 D:画像リンク1 E:画像2 F:画像リンク2 G:画像3 H:画像リンク3 I:ステータス J:メモ K:リプライテキスト
COL_TEXT = 1         # B: 投稿テキスト
COL_IMG_LINK = 3     # D: 画像リンク1
COL_IMG2_LINK = 5    # F: 画像リンク2
COL_IMG3_LINK = 7    # H: 画像リンク3
COL_TIME = 0         # A: 投稿日時
COL_STATUS = 8       # I: ステータス
COL_MEMO = 9         # J: メモ
COL_REPLY = 10       # K: リプライテキスト

# ステータス値
STATUS_SCHEDULED = '投稿予約'
STATUS_POSTED = '投稿済み'
STATUS_FAILED = '投稿失敗'

# APIエンドポイント（2026年時点）
X_POST_ENDPOINTS = [
    os.getenv('X_POST_API_URL', 'https://api.x.com/2/tweets'),
    'https://api.twitter.com/2/tweets',  # 後方互換フォールバック
]


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


def _sync_board(memo, post_id=""):
    """投稿できたことを共有ボードに記録する。失敗しても投稿処理は止めない。"""
    try:
        import board_sync
        no = board_sync.article_no_from_memo(memo)
        if no:
            board_sync.mark_published(no, post_id, logger)
    except Exception as e:
        logger.warning(f"共有ボードへの記録をとばしました: {type(e).__name__}: {e}")


def upload_image_to_x(image_url, auth):
    """Google Drive画像をダウンロードしてX APIにアップロード"""
    try:
        # Drive URLからファイルIDを抽出。
        # 2026-09-06: 共有ボードは thumbnail?id=... 形式を渡すが、
        # /d/ 形式しか見ておらず画像なしで投稿していた（ART-0049）。
        # Instagram側は両方に対応していたので、Xだけが取りこぼしていた
        if 'drive.google.com' in image_url:
            file_id = None
            if '/d/' in image_url:
                file_id = image_url.split('/d/')[1].split('/')[0].split('?')[0]
            else:
                m = re.search(r'[?&]id=([A-Za-z0-9_-]{10,})', image_url)
                if m:
                    file_id = m.group(1)
            if not file_id:
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


def _parse_json_safely(resp: requests.Response) -> Optional[Any]:
    """JSONレスポンスを安全にパース（空ボディ対応）"""
    body = (resp.text or '').strip()
    if not body:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def _extract_error_message(resp: requests.Response) -> str:
    """X APIのエラーメッセージを抽出"""
    data = _parse_json_safely(resp)
    if not data:
        return '(レスポンス本文なし)'

    if isinstance(data, dict):
        if 'detail' in data and data['detail']:
            return str(data['detail'])
        errors = data.get('errors')
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                return str(first.get('message') or first.get('detail') or first)
            return str(first)
    return str(data)


def post_tweet(text, image_urls=None, auth=None, reply_to=None):
    """ツイートを投稿（画像付き・リプライ対応）"""
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
    if reply_to:
        payload['reply'] = {'in_reply_to_tweet_id': reply_to}

    last_error = None
    for endpoint in X_POST_ENDPOINTS:
        try:
            resp = requests.post(
                endpoint,
                auth=auth,
                json=payload,
                timeout=30
            )
        except requests.RequestException as e:
            last_error = f"{endpoint} への接続失敗: {e}"
            logger.error(last_error)
            continue

        req_id = resp.headers.get('x-request-id', '-')
        if resp.status_code in (200, 201):
            data = _parse_json_safely(resp) or {}
            tweet_id = ((data.get('data') or {}).get('id')) if isinstance(data, dict) else None
            if tweet_id:
                logger.info(f"投稿成功! Tweet ID: {tweet_id} (画像{len(media_ids)}枚) endpoint={endpoint} request_id={req_id}")
                return tweet_id
            logger.error(f"投稿成功ステータスだがTweet IDを取得できませんでした endpoint={endpoint} request_id={req_id}")
            return None

        error_message = _extract_error_message(resp)
        last_error = f"投稿失敗 status={resp.status_code} endpoint={endpoint} request_id={req_id} error={error_message}"
        logger.error(last_error)

        # 認可/課金系のエラーは別エンドポイントで再試行しても改善しないため即終了
        if resp.status_code in (400, 401, 402, 403):
            break

    if last_error:
        logger.error(f"最終エラー: {last_error}")
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
                # 複数フォーマットに対応
                normalized = post_time_str.replace('/', '-')  # スラッシュをハイフンに統一
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
            'text': row[COL_TEXT],
            'image_urls': image_urls,
            'post_time': post_time_str,
            'reply_text': row[COL_REPLY].strip() if len(row) > COL_REPLY and row[COL_REPLY] else '',
            # どの記事の投稿かを控える。投稿後に共有ボードへ伝えるために使う
            'memo': row[COL_MEMO].strip() if len(row) > COL_MEMO and row[COL_MEMO] else '',
        })

    return posts


def _build_x_post_url(tweet_id: str) -> Optional[str]:
    """Tweet IDから閲覧用URLを組み立てる。ユーザー名は環境変数から"""
    if not tweet_id:
        return None
    username = os.getenv('X_USERNAME', 'SFH_Science')
    return f"https://x.com/{username}/status/{tweet_id}"


def run_scheduled(dry_run=False):
    """予約投稿を実行"""
    logger.info("=" * 50)
    logger.info(f"X自動投稿チェック開始 {'(ドライラン)' if dry_run else ''}")

    # 緊急停止スイッチ。シートの『運用スイッチ』B2 が『停止』なら1件も投稿しない。
    # 読めなかった場合も停止側に倒す（投稿は取り消せないため）。
    if not dry_run:
        from posting_switch import is_posting_enabled
        if not is_posting_enabled(logger):
            logger.info("投稿スイッチにより中止しました")
            return

    ws = get_sheet()
    posts = get_scheduled_posts(ws)
    notifier = build_default_notifier()

    if not posts:
        logger.info("投稿すべき予約はありません")
        return

    logger.info(f"{len(posts)}件の投稿を実行します")
    auth = get_x_auth()

    for post in posts:
        logger.info(f"Row {post['row']}: {post['text'][:50]}...")

        if dry_run:
            logger.info(f"  [ドライラン] スキップ (画像{len(post['image_urls'])}枚)")
            continue

        tweet_id = post_tweet(post['text'], post['image_urls'], auth)

        if tweet_id:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            memo = f"投稿済 {timestamp} ID:{tweet_id}"

            # リプライ送信
            reply_text = post.get('reply_text', '')
            reply_id = None
            if reply_text:
                time.sleep(5)  # 親ツイート反映を待つ
                reply_id = post_tweet(reply_text, auth=auth, reply_to=tweet_id)
                if reply_id:
                    logger.info(f"  リプライ成功! Reply ID: {reply_id}")
                    memo += f" Reply:{reply_id}"
                else:
                    logger.warning(f"  リプライ失敗（本体は投稿済み）")
                    memo += " リプライ失敗"

            # ステータスを「投稿済み」に更新
            ws.update_cell(post['row'], COL_STATUS + 1, STATUS_POSTED)
            ws.update_cell(post['row'], COL_MEMO + 1, memo)
            logger.info(f"  ステータス更新完了")

            # 共有ボードにも伝える。ここが無いと圭一郎さんの画面は
            # 「投稿予約」のままで、出たのかどうか分からない（2026-09-06）
            _sync_board(post.get('memo', ''), str(tweet_id))

            # 通知
            post_url = _build_x_post_url(tweet_id)
            notifier.notify_success(
                platform='X (Twitter)',
                caption=post['text'],
                post_url=post_url,
                image_url=post['image_urls'][0] if post['image_urls'] else None,
                post_id=tweet_id,
            )
        else:
            ws.update_cell(post['row'], COL_STATUS + 1, STATUS_FAILED)
            logger.error(f"  投稿失敗 - ステータスを「投稿失敗」に更新")
            notifier.notify_failure(
                platform='X (Twitter)',
                caption=post['text'],
                error='投稿API呼び出しが失敗しました（詳細はログを参照）',
            )

        # レート制限対策
        time.sleep(3)

    logger.info("自動投稿チェック完了")


def list_scheduled():
    """予約済み一覧を表示"""
    ws = get_sheet()
    all_data = ws.get_all_values()

    print("\n=== X投稿キュー 予約状況 ===\n")
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
        post_url = _build_x_post_url(tweet_id)
        print(f"\n✅ 投稿成功! {post_url}")

        notifier = build_default_notifier()
        notifier.notify_success(
            platform='X (Twitter)',
            caption=text,
            post_url=post_url,
            image_url=image_urls[0] if image_urls else None,
            post_id=tweet_id,
        )
    else:
        print("\n❌ 投稿失敗")
        notifier = build_default_notifier()
        notifier.notify_failure(
            platform='X (Twitter)',
            caption=text,
            error='投稿API呼び出しが失敗しました',
        )


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
