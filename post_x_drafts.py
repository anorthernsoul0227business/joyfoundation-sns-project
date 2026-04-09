#!/usr/bin/env python3
"""X投稿スクリプト - 投稿プランの下書きを一括投稿"""

import json
import time
import sys
import os
from dotenv import load_dotenv
import tweepy

# Load environment variables
load_dotenv()

def get_client():
    """Tweepy v2 clientを取得"""
    client = tweepy.Client(
        consumer_key=os.getenv('X_CONSUMER_KEY'),
        consumer_secret=os.getenv('X_CONSUMER_SECRET'),
        access_token=os.getenv('X_ACCESS_TOKEN'),
        access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET'),
    )
    return client

def post_single(client, text, dry_run=False):
    """1件投稿"""
    if dry_run:
        print(f"  [DRY RUN] {len(text)}文字: {text[:50]}...")
        return True
    try:
        response = client.create_tweet(text=text)
        print(f"  ✓ 投稿成功 (ID: {response.data['id']})")
        return True
    except tweepy.errors.TweepyException as e:
        print(f"  ✗ エラー: {e}")
        return False

def main():
    # Load posts
    with open('/tmp/x_drafts.json', 'r') as f:
        posts = json.load(f)

    mode = sys.argv[1] if len(sys.argv) > 1 else 'test'

    if mode == 'test':
        # テスト: 1本だけ投稿
        print("=== テストモード: 1本だけ投稿 ===")
        client = get_client()
        post = posts[1]  # 2本目（名言投稿）をテスト
        print(f"投稿内容:\n{post['text']}\n")
        print(f"文字数: {post['chars']}")
        result = post_single(client, post['text'])
        if result:
            print("\nテスト成功！ 'all' モードで全件投稿できます")
            print("使い方: python3 post_x_drafts.py all")

    elif mode == 'dry':
        # ドライラン: 全件を表示のみ
        print(f"=== ドライラン: {len(posts)}本 ===\n")
        for i, post in enumerate(posts):
            print(f"{i+1}. [{post['chars']}字] {post['title']}")
            post_single(None, post['text'], dry_run=True)
            print()

    elif mode == 'all':
        # 全件投稿（自己紹介除く）
        client = get_client()
        print(f"=== 全件投稿: {len(posts) - 1}本（自己紹介除く）===\n")
        success = 0
        fail = 0
        for i, post in enumerate(posts):
            if i == 0:  # 自己紹介は280文字超過のためスキップ
                print(f"{i+1}. [SKIP] {post['title']} (280文字超過)")
                continue
            print(f"{i+1}. [{post['chars']}字] {post['title']}")
            result = post_single(client, post['text'])
            if result:
                success += 1
            else:
                fail += 1
            time.sleep(2)  # レート制限対策
        print(f"\n=== 完了: 成功 {success}本 / 失敗 {fail}本 ===")

    else:
        print("使い方:")
        print("  python3 post_x_drafts.py test  # テスト1本")
        print("  python3 post_x_drafts.py dry   # ドライラン")
        print("  python3 post_x_drafts.py all   # 全件投稿")

if __name__ == '__main__':
    main()
