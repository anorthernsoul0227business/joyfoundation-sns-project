#!/usr/bin/env python3
"""X投稿スケジューラー - 投稿管理・確認・自動投稿"""

import json
import time
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import tweepy

load_dotenv()

SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), 'x_schedule.json')

def get_client():
    client = tweepy.Client(
        consumer_key=os.getenv('X_CONSUMER_KEY'),
        consumer_secret=os.getenv('X_CONSUMER_SECRET'),
        access_token=os.getenv('X_ACCESS_TOKEN'),
        access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET'),
    )
    return client

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    return []

def save_schedule(schedule):
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

def init_schedule():
    """JSONから初期スケジュールを作成"""
    with open('/tmp/x_drafts.json', 'r') as f:
        posts = json.load(f)

    schedule = []
    for i, post in enumerate(posts):
        schedule.append({
            'id': i + 1,
            'title': post['title'],
            'text': post['text'],
            'chars': post['chars'],
            'status': 'draft',  # draft / scheduled / posted / skipped
            'scheduled_at': None,
            'posted_at': None,
            'tweet_id': None,
        })
    save_schedule(schedule)
    print(f"✓ {len(schedule)}本のスケジュールを作成しました → {SCHEDULE_FILE}")

def show_list(filter_status=None):
    """一覧表示"""
    schedule = load_schedule()
    if not schedule:
        print("スケジュールがありません。'init' で作成してください")
        return

    status_icons = {'draft': '📝', 'scheduled': '🕐', 'posted': '✅', 'skipped': '⏭️'}

    for item in schedule:
        if filter_status and item['status'] != filter_status:
            continue
        icon = status_icons.get(item['status'], '?')
        sched = f" → {item['scheduled_at']}" if item['scheduled_at'] else ''
        print(f"  {icon} {item['id']:2d}. [{item['chars']:3d}字] {item['title'][:35]}{sched}")

    counts = {}
    for item in schedule:
        counts[item['status']] = counts.get(item['status'], 0) + 1
    print(f"\n  合計: {' / '.join(f'{status_icons[k]}{v}本' for k, v in counts.items())}")

def show_detail(post_id):
    """投稿詳細表示"""
    schedule = load_schedule()
    item = next((x for x in schedule if x['id'] == post_id), None)
    if not item:
        print(f"ID {post_id} が見つかりません")
        return

    status_icons = {'draft': '📝下書き', 'scheduled': '🕐予約済', 'posted': '✅投稿済', 'skipped': '⏭️スキップ'}
    print(f"\n{'='*50}")
    print(f"ID: {item['id']}  状態: {status_icons[item['status']]}")
    print(f"タイトル: {item['title']}")
    print(f"文字数: {item['chars']}")
    if item['scheduled_at']:
        print(f"予約日時: {item['scheduled_at']}")
    if item['posted_at']:
        print(f"投稿日時: {item['posted_at']}")
    print(f"{'='*50}")
    print(item['text'])
    print(f"{'='*50}\n")

def schedule_post(post_id, date_str):
    """投稿を予約"""
    schedule = load_schedule()
    item = next((x for x in schedule if x['id'] == post_id), None)
    if not item:
        print(f"ID {post_id} が見つかりません")
        return
    item['status'] = 'scheduled'
    item['scheduled_at'] = date_str
    save_schedule(schedule)
    print(f"✓ ID {post_id} を {date_str} に予約しました")

def schedule_bulk(start_date, posts_per_day=2, hour1="09:00", hour2="18:00"):
    """一括予約（1日2本ずつ）"""
    schedule = load_schedule()
    drafts = [x for x in schedule if x['status'] == 'draft']

    if not drafts:
        print("予約する下書きがありません")
        return

    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    hours = [hour1, hour2]
    count = 0

    for i, item in enumerate(drafts):
        hour = hours[count % posts_per_day]
        date_str = f"{current_date.strftime('%Y-%m-%d')} {hour}"
        item['status'] = 'scheduled'
        item['scheduled_at'] = date_str
        count += 1
        if count % posts_per_day == 0:
            current_date += timedelta(days=1)

    save_schedule(schedule)
    print(f"✓ {count}本を {start_date} から1日{posts_per_day}本ずつ予約しました")

def post_now(post_id):
    """即時投稿"""
    schedule = load_schedule()
    item = next((x for x in schedule if x['id'] == post_id), None)
    if not item:
        print(f"ID {post_id} が見つかりません")
        return
    if item['status'] == 'posted':
        print(f"ID {post_id} は既に投稿済みです")
        return

    print(f"投稿内容:\n{item['text']}\n")
    confirm = input("この投稿を公開しますか？ (y/N): ")
    if confirm.lower() != 'y':
        print("キャンセルしました")
        return

    client = get_client()
    try:
        response = client.create_tweet(text=item['text'])
        item['status'] = 'posted'
        item['posted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        item['tweet_id'] = str(response.data['id'])
        save_schedule(schedule)
        print(f"✓ 投稿成功 (ID: {response.data['id']})")
    except tweepy.errors.TweepyException as e:
        print(f"✗ エラー: {e}")

def post_scheduled():
    """予約時刻を過ぎた投稿を実行"""
    schedule = load_schedule()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    to_post = [x for x in schedule if x['status'] == 'scheduled' and x['scheduled_at'] and x['scheduled_at'] <= now]

    if not to_post:
        print("現在投稿すべき予約はありません")
        return

    client = get_client()
    for item in to_post:
        print(f"投稿中: {item['id']}. {item['title'][:30]}...")
        try:
            response = client.create_tweet(text=item['text'])
            item['status'] = 'posted'
            item['posted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            item['tweet_id'] = str(response.data['id'])
            print(f"  ✓ 成功")
            time.sleep(2)
        except tweepy.errors.TweepyException as e:
            print(f"  ✗ エラー: {e}")

    save_schedule(schedule)
    print(f"\n完了: {len(to_post)}本処理しました")

def edit_text(post_id):
    """投稿テキストを編集（エディタで開く）"""
    schedule = load_schedule()
    item = next((x for x in schedule if x['id'] == post_id), None)
    if not item:
        print(f"ID {post_id} が見つかりません")
        return

    tmp_file = f'/tmp/x_edit_{post_id}.txt'
    with open(tmp_file, 'w') as f:
        f.write(item['text'])

    os.system(f'open -e {tmp_file}')
    input("編集が完了したらEnterを押してください...")

    with open(tmp_file, 'r') as f:
        new_text = f.read().strip()

    if new_text != item['text']:
        item['text'] = new_text
        item['chars'] = len(new_text)
        save_schedule(schedule)
        print(f"✓ 更新しました ({item['chars']}文字)")
    else:
        print("変更なし")

def main():
    if len(sys.argv) < 2:
        print("""
X投稿スケジューラー
==================
使い方:
  python3 x_scheduler.py init                    # スケジュール初期化
  python3 x_scheduler.py list                    # 一覧表示
  python3 x_scheduler.py list draft              # 下書きのみ表示
  python3 x_scheduler.py list scheduled          # 予約済のみ表示
  python3 x_scheduler.py show 5                  # ID 5 の詳細表示
  python3 x_scheduler.py schedule 5 "2026-03-25 09:00"  # ID 5 を予約
  python3 x_scheduler.py bulk "2026-03-25"       # 全下書きを一括予約（1日2本）
  python3 x_scheduler.py post 5                  # ID 5 を即時投稿（確認あり）
  python3 x_scheduler.py run                     # 予約時刻の投稿を実行
  python3 x_scheduler.py edit 5                  # ID 5 のテキストを編集
""")
        return

    cmd = sys.argv[1]

    if cmd == 'init':
        init_schedule()
    elif cmd == 'list':
        filter_status = sys.argv[2] if len(sys.argv) > 2 else None
        show_list(filter_status)
    elif cmd == 'show':
        show_detail(int(sys.argv[2]))
    elif cmd == 'schedule':
        schedule_post(int(sys.argv[2]), sys.argv[3])
    elif cmd == 'bulk':
        start = sys.argv[2]
        ppd = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        schedule_bulk(start, ppd)
    elif cmd == 'post':
        post_now(int(sys.argv[2]))
    elif cmd == 'run':
        post_scheduled()
    elif cmd == 'edit':
        edit_text(int(sys.argv[2]))
    else:
        print(f"不明なコマンド: {cmd}")

if __name__ == '__main__':
    main()
