#!/usr/bin/env python3
"""X投稿スケジュールをCSVにエクスポート（Google Sheets用）"""

import json
import csv
import os

SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), 'x_schedule.json')
CSV_FILE = os.path.join(os.path.dirname(__file__), 'X投稿スケジュール.csv')

def export_csv():
    with open(SCHEDULE_FILE, 'r') as f:
        schedule = json.load(f)

    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ID', 'タイトル', '投稿テキスト', '文字数',
            'ステータス', '予約日時', '投稿日時',
            '圭一郎さん確認', 'メモ'
        ])
        for item in schedule:
            status_map = {
                'draft': '下書き',
                'scheduled': '予約済',
                'posted': '投稿済',
                'skipped': 'スキップ'
            }
            writer.writerow([
                item['id'],
                item['title'],
                item['text'],
                item['chars'],
                status_map.get(item['status'], item['status']),
                item['scheduled_at'] or '',
                item['posted_at'] or '',
                '',  # 圭一郎さん確認欄
                '',  # メモ欄
            ])

    print(f"✓ CSV出力完了 → {CSV_FILE}")
    print(f"  {len(schedule)}本のデータをエクスポートしました")
    print(f"\n次の手順:")
    print(f"  1. Google Sheets (sheets.google.com) を開く")
    print(f"  2. 新規スプレッドシート作成")
    print(f"  3. ファイル → インポート → アップロード")
    print(f"  4. '{CSV_FILE}' を選択")
    print(f"  5. 共有 → kita@h-garden.com を追加")

if __name__ == '__main__':
    export_csv()
