#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カンガルーカップ2026のメール添付ファイルをGmail APIでダウンロードし、
Google Driveにアップロードする。

Gmail APIアクセスにはOAuth認証が必要。
初回実行時にブラウザで認証フローが開きます。
"""

import os
import sys
import base64
import tempfile
from pathlib import Path

from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ===== 設定 =====
SA_FILE = os.path.expanduser('~/.config/gspread/service_account.json')
DRIVE_FOLDER_ID = '14F_TS3d9t7x2zTCjnFezFEk6_KnuyHqk'

# メールのMessage IDs（2026-04-09 圭一郎さんからのメール）
MESSAGE_IDS = [
    '19d71ace78f2d32d',  # RE: IGイベント投稿確認（DOCX, PDF, 写真3枚）
    '19d71b4782b8ab8b',  # カンガルーカップウエブサイト（写真1枚）
]

# Gmail APIにはOAuth必要。まずサービスアカウントでのDrive部分だけ準備
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
drive_creds = SACredentials.from_service_account_file(SA_FILE, scopes=DRIVE_SCOPES)
drive_service = build('drive', 'v3', credentials=drive_creds)


def upload_to_drive(filepath, filename, mime_type=None):
    """ファイルをDriveにアップロード"""
    if mime_type is None:
        ext = Path(filename).suffix.lower()
        mime_map = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        mime_type = mime_map.get(ext, 'application/octet-stream')

    metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(filepath, mimetype=mime_type)
    f = drive_service.files().create(body=metadata, media_body=media, fields='id,webViewLink').execute()
    print(f"  uploaded: {filename} -> {f.get('webViewLink', f['id'])}")
    return f['id']


def try_gmail_oauth():
    """OAuth認証でGmail APIにアクセスを試みる"""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle

        token_path = os.path.expanduser('~/.config/gmail_token.pickle')
        creds = None

        if os.path.exists(token_path):
            with open(token_path, 'rb') as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # OAuth client credentials が必要
                client_secret = os.path.expanduser('~/.config/gmail_client_secret.json')
                if not os.path.exists(client_secret):
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secret,
                    scopes=['https://www.googleapis.com/auth/gmail.readonly']
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)

        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        print(f"  OAuth認証エラー: {e}")
        return None


def download_from_gmail(gmail_service, message_id):
    """メールから添付ファイルをダウンロード"""
    msg = gmail_service.users().messages().get(userId='me', id=message_id).execute()
    parts = msg.get('payload', {}).get('parts', [])

    downloaded = []
    for part in parts:
        filename = part.get('filename', '')
        if not filename:
            continue

        att_id = part['body'].get('attachmentId')
        if not att_id:
            continue

        att = gmail_service.users().messages().attachments().get(
            userId='me', messageId=message_id, id=att_id
        ).execute()

        data = base64.urlsafe_b64decode(att['data'])
        tmp_path = os.path.join(tempfile.gettempdir(), filename)
        with open(tmp_path, 'wb') as f:
            f.write(data)

        print(f"  downloaded: {filename} ({len(data)} bytes)")
        downloaded.append((tmp_path, filename))

    return downloaded


def main():
    print("=== カンガルーカップ2026 添付ファイル保存 ===\n")

    # Gmail OAuth を試す
    print("Gmail API 認証中...")
    gmail = try_gmail_oauth()

    if gmail:
        print("Gmail API 認証成功\n")
        for msg_id in MESSAGE_IDS:
            print(f"メッセージ {msg_id} の添付ファイルをダウンロード中...")
            files = download_from_gmail(gmail, msg_id)
            for filepath, filename in files:
                upload_to_drive(filepath, filename)
                os.remove(filepath)
            print()

        print("完了! 全ファイルをDriveにアップロードしました")
        print(f"フォルダ: https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}")
    else:
        print("\nGmail OAuth認証が利用できません。")
        print("代替手段: 以下のローカルファイルを手動でDriveフォルダにアップロードしてください。")
        print(f"\nDriveフォルダ: https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}")
        print("\n添付ファイル一覧（メールから手動保存が必要）:")
        print("  1. カンガルーカップ2026 SNS用.DOCX")
        print("  2. 国際カンガルーカップ開催要項2026.pdf")
        print("  3. 2025.5.1 Kangaroo Cup2025.jpg")
        print("  4. IMG_0730.jpg")
        print("  5. 2025.5.1 Kangaroo Cup2025 IMG_0506.jpeg")
        print("  6. IMG_0744.jpg")

        # ローカルに保存されたファイルがあればアップロード
        local_dir = os.path.expanduser('~/Downloads')
        target_files = [
            'カンガルーカップ2026 SNS用.DOCX',
            '国際カンガルーカップ開催要項2026.pdf',
            '2025.5.1 Kangaroo Cup2025.jpg',
            'IMG_0730.jpg',
            '2025.5.1 Kangaroo Cup2025　IMG_0506.jpeg',
            'IMG_0744.jpg',
        ]

        print(f"\n~/Downloads フォルダをチェック中...")
        found = 0
        for fn in target_files:
            fp = os.path.join(local_dir, fn)
            if os.path.exists(fp):
                print(f"  発見: {fn}")
                upload_to_drive(fp, fn)
                found += 1

        if found > 0:
            print(f"\n{found}ファイルをDriveにアップロードしました")
        else:
            print("\nDownloadsフォルダにファイルが見つかりません。")
            print("Gmailから添付ファイルを保存後、再度このスクリプトを実行してください。")
            print("または、Driveフォルダに直接ドラッグ&ドロップしてください。")


if __name__ == '__main__':
    main()
