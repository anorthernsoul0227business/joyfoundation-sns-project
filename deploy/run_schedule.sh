#!/bin/bash
# 毎朝 8:00。カレンダーを取り込んでから、承認済み記事の投稿日を決める。
# 順番が大事: 新しい予定が events に入っていないと、開催日の逆算ができない。
set -u
cd "$(dirname "$0")"
/usr/bin/python3 sync_events.py         || echo "[warn] カレンダーの取り込みに失敗。前回の予定で続行します"
# 新しい催しが入っていれば告知記事を作る。生成に時間がかかるので投稿日決定より前に置く
/usr/bin/python3 generate_event_posts.py || echo "[warn] 告知記事の生成に失敗。次回に持ち越します"
/usr/bin/python3 schedule_posts.py
# 圭一郎さんのメモに返事がないものを知らせる。
# 書き込まれるだけで誰も見に行っていなかった（2026-09-08 に発覚）
/usr/bin/python3 check_ideas.py         || echo "[warn] メモの確認に失敗しました"
# note など手で投稿する記事を、予定日の朝に知らせる。
# 2026-09-19: 知らせる仕組みがなく、ART-0078 が10日放置され開催日を過ぎた
/usr/bin/python3 notify_manual_posts.py || echo "[warn] 手投稿の通知に失敗しました"
# 開催が近い告知が未確認のときだけ、圭一郎さんに追加でお知らせする。
# 週1回では間に合わないことがある（2026-09-20 に3件が出せなくなった）
/usr/bin/python3 notify_owner.py --urgent-only || echo "[warn] お急ぎの通知に失敗しました"
