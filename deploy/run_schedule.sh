#!/bin/bash
# 毎朝 8:00。カレンダーを取り込んでから、承認済み記事の投稿日を決める。
# 順番が大事: 新しい予定が events に入っていないと、開催日の逆算ができない。
set -u
cd "$(dirname "$0")"
/usr/bin/python3 sync_events.py    || echo "[warn] カレンダーの取り込みに失敗。前回の予定で続行します"
/usr/bin/python3 schedule_posts.py
