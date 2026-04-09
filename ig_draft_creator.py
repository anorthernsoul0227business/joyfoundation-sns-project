#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instagram下書き作成（Playwright使用）
画像添付→キャプション入力→下書き保存を自動化
"""

import sys
import time
from playwright.sync_api import sync_playwright

def create_ig_draft(image_path, caption, headless=False):
    """Instagramに下書きを作成する"""

    with sync_playwright() as p:
        # ブラウザ起動（headless=Falseで目視確認可能）
        browser = p.chromium.launch(
            headless=headless,
            channel="chrome"  # 既存のChromeプロファイルを使用
        )

        # 既存のCookieを使うためにユーザーデータディレクトリを指定
        context = browser.new_context(
            storage_state=None,
            viewport={"width": 1200, "height": 800}
        )
        page = context.new_page()

        print("Instagramにアクセス中...")
        page.goto("https://www.instagram.com/")
        page.wait_for_timeout(3000)

        # ログイン状態確認
        if "login" in page.url.lower():
            print("ログインが必要です。ブラウザでログインしてください。")
            input("ログイン後、Enterを押してください...")

        print("新規投稿作成...")
        # 「作成」ボタンをクリック
        create_btn = page.locator('a:has-text("作成"), svg[aria-label="新規投稿"]').first
        create_btn.click()
        page.wait_for_timeout(1000)

        # 「投稿」を選択
        post_btn = page.locator('text=投稿').first
        if post_btn.is_visible():
            post_btn.click()
            page.wait_for_timeout(1000)

        print(f"画像をアップロード中: {image_path}")
        # ファイルアップロード（hidden input[type=file]を見つけて設定）
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(image_path)
        page.wait_for_timeout(3000)

        print("トリミング画面をスキップ...")
        # 「次へ」ボタン
        next_btn = page.locator('text=次へ, div[role="button"]:has-text("次へ")').first
        if next_btn.is_visible():
            next_btn.click()
            page.wait_for_timeout(2000)

        # フィルター画面の「次へ」
        next_btn2 = page.locator('text=次へ, div[role="button"]:has-text("次へ")').first
        if next_btn2.is_visible():
            next_btn2.click()
            page.wait_for_timeout(2000)

        print("キャプション入力中...")
        # キャプション入力欄
        caption_area = page.locator('textarea[aria-label*="キャプション"], div[aria-label*="キャプション"], textarea[placeholder*="キャプション"]').first
        if caption_area.is_visible():
            caption_area.click()
            caption_area.fill(caption)
            page.wait_for_timeout(1000)
        else:
            print("キャプション欄が見つかりません。手動で入力してください。")

        print("\n下書きとして保存するには、ブラウザで「戻る」→「下書きを保存」を選択してください。")
        print("または「シェア」をクリックして投稿できます。")
        input("\n操作完了後、Enterを押してください...")

        browser.close()
        print("完了！")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 ig_draft_creator.py <image_path> <caption_file>")
        print("  caption_file: キャプションテキストのファイルパス")
        sys.exit(1)

    image_path = sys.argv[1]
    caption_file = sys.argv[2]

    with open(caption_file, 'r') as f:
        caption = f.read()

    create_ig_draft(image_path, caption, headless=False)
