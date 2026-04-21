#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
イベント投稿シート → 投稿キュー 自動展開パイプライン

IGイベント投稿 / Xイベント投稿 の「下書き + 投稿予定日あり + 未来日」を
IG投稿キュー / X投稿キュー にコピー（重複防止付き）。

使い方:
  python3 push_events_to_queue.py           # ドライラン（デフォルト）
  python3 push_events_to_queue.py --apply   # 実適用
  python3 push_events_to_queue.py --ig-only # IGのみ
  python3 push_events_to_queue.py --x-only  # Xのみ
"""

import os
import sys
import re
import argparse
import logging
from datetime import datetime, date

import gspread

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'push_events.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SPREADSHEET_ID = '1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM'
DEFAULT_POST_TIME = '12:00'
ASSUMED_YEAR = 2026
STATUS_QUEUED = '投稿予約'
STATUS_DRAFT_DONE = 'キュー投入済'


def parse_sched_date(s: str, today: date):
    """「4/8」「4/21(月)」「5月下旬」等を date に変換。曖昧・不明はNone"""
    if not s or not s.strip():
        return None, 'empty'
    s = s.strip()

    m = re.match(r'^(\d{1,2})/(\d{1,2})', s)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            return date(ASSUMED_YEAR, month, day), None
        except ValueError:
            return None, f'invalid date: {s}'

    logger.warning(f'パース不可・スキップ: "{s}"')
    return None, f'unparseable: {s}'


def col_letter(n: int) -> str:
    s = ''
    n += 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def get_queued_sources(ws_queue, memo_col_idx=9):
    """投稿キューのメモ列から既展開ソース識別子を抽出"""
    sources = set()
    rows = ws_queue.get_all_values()
    for r in rows[1:]:
        if len(r) > memo_col_idx:
            memo = r[memo_col_idx]
            m = re.search(r'SRC:([^\s|]+)', memo)
            if m:
                sources.add(m.group(1))
    return sources


def push_ig(sh, apply_mode: bool, today: date):
    """IGイベント投稿 → IG投稿キュー"""
    ws_src = sh.worksheet('IGイベント投稿')
    ws_dst = sh.worksheet('IG投稿キュー')
    src_rows = ws_src.get_all_values()

    # 列インデックス（IGイベント投稿）
    NO, NAME = 0, 1
    CAPTION = 6
    IMG_LINK = 9
    SCHED = 11
    STATUS = 12

    existing = get_queued_sources(ws_dst, memo_col_idx=9)
    logger.info(f'IG既展開ソース: {len(existing)}件')

    candidates = []
    for r in src_rows[1:]:
        if not r[NO] or r[NO].startswith('M'):
            continue
        if r[STATUS] != '下書き':
            continue
        src_id = f'IG-No{r[NO]}'
        if src_id in existing:
            continue
        d, err = parse_sched_date(r[SCHED], today)
        if d is None:
            logger.warning(f'{src_id} ({r[NAME][:25]}) 予定日パース不可 [{err}] → スキップ')
            continue
        if d < today:
            logger.info(f'{src_id} ({r[NAME][:25]}) 予定日 {d} は過去 → スキップ')
            continue
        if not r[CAPTION].strip():
            logger.warning(f'{src_id} ({r[NAME][:25]}) キャプション空 → スキップ')
            continue

        post_dt = f'{d.strftime("%Y/%m/%d")} {DEFAULT_POST_TIME}:00'
        candidates.append({
            'src_id': src_id,
            'name': r[NAME],
            'post_dt': post_dt,
            'caption': r[CAPTION],
            'img_link': r[IMG_LINK],
            'sched_date': d,
            'src_row': src_rows.index(r) + 1
        })

    candidates.sort(key=lambda x: x['sched_date'])
    logger.info(f'IG投入候補: {len(candidates)}件')
    for c in candidates:
        logger.info(f'  [{c["src_id"]}] {c["post_dt"]} | {c["name"][:35]}')

    if not apply_mode or not candidates:
        return len(candidates), 0

    # 追記
    all_dst = ws_dst.get_all_values()
    start_row = 2
    for i, rr in enumerate(all_dst[1:], 2):
        if any(c.strip() for c in rr):
            start_row = i + 1

    new_rows = []
    for c in candidates:
        row = [
            c['post_dt'],  # A
            c['caption'],  # B
            '',            # C
            c['img_link'], # D
            '', '',        # E, F
            '', '',        # G, H
            STATUS_QUEUED, # I
            f'SRC:{c["src_id"]} | {c["name"][:30]}'  # J
        ]
        new_rows.append(row)

    end_row = start_row + len(new_rows) - 1
    ws_dst.update(range_name=f'A{start_row}:J{end_row}',
                  values=new_rows, value_input_option='USER_ENTERED')

    # ソースシート側のステータス更新
    status_updates = []
    for c in candidates:
        status_updates.append({
            'range': f'{col_letter(STATUS)}{c["src_row"]}',
            'values': [[STATUS_DRAFT_DONE]]
        })
    ws_src.batch_update(status_updates, value_input_option='USER_ENTERED')

    logger.info(f'✅ IG投稿キュー 行{start_row}〜{end_row} に {len(new_rows)}件追加')
    return len(candidates), len(new_rows)


def push_x(sh, apply_mode: bool, today: date):
    """Xイベント投稿 → X投稿キュー"""
    ws_src = sh.worksheet('Xイベント投稿')
    ws_dst = sh.worksheet('X投稿キュー')
    src_rows = ws_src.get_all_values()

    # 列インデックス（Xイベント投稿）
    NAME = 0
    TEXT = 5
    IMG_LINK = 8
    SCHED = 10
    STATUS = 11

    existing = get_queued_sources(ws_dst, memo_col_idx=9)
    logger.info(f'X既展開ソース: {len(existing)}件')

    candidates = []
    for idx, r in enumerate(src_rows[1:], 2):
        if len(r) < 12:
            continue
        name = r[NAME].strip()
        if not name:
            continue
        if r[STATUS] != '下書き':
            continue
        src_id = f'X-row{idx}'
        if src_id in existing:
            continue
        d, err = parse_sched_date(r[SCHED], today)
        if d is None:
            logger.warning(f'{src_id} ({name[:25]}) 予定日パース不可 [{err}] → スキップ')
            continue
        if d < today:
            logger.info(f'{src_id} ({name[:25]}) 予定日 {d} は過去 → スキップ')
            continue
        if not r[TEXT].strip():
            logger.warning(f'{src_id} ({name[:25]}) テキスト空 → スキップ')
            continue

        post_dt = f'{d.strftime("%Y-%m-%d")} {DEFAULT_POST_TIME}'
        candidates.append({
            'src_id': src_id,
            'name': name,
            'post_dt': post_dt,
            'text': r[TEXT],
            'img_link': r[IMG_LINK],
            'sched_date': d,
            'src_row': idx
        })

    candidates.sort(key=lambda x: x['sched_date'])
    logger.info(f'X投入候補: {len(candidates)}件')
    for c in candidates:
        logger.info(f'  [{c["src_id"]}] {c["post_dt"]} | {c["name"][:35]}')

    if not apply_mode or not candidates:
        return len(candidates), 0

    all_dst = ws_dst.get_all_values()
    start_row = 2
    for i, rr in enumerate(all_dst[1:], 2):
        if any(c.strip() for c in rr):
            start_row = i + 1

    new_rows = []
    for c in candidates:
        row = [
            c['post_dt'],   # A
            c['text'],      # B
            '',             # C
            c['img_link'],  # D
            '', '',         # E, F
            '', '',         # G, H
            STATUS_QUEUED,  # I
            f'SRC:{c["src_id"]} | {c["name"][:30]}',  # J
            ''              # K リプライ
        ]
        new_rows.append(row)

    end_row = start_row + len(new_rows) - 1
    ws_dst.update(range_name=f'A{start_row}:K{end_row}',
                  values=new_rows, value_input_option='USER_ENTERED')

    status_updates = []
    for c in candidates:
        status_updates.append({
            'range': f'{col_letter(STATUS)}{c["src_row"]}',
            'values': [[STATUS_DRAFT_DONE]]
        })
    ws_src.batch_update(status_updates, value_input_option='USER_ENTERED')

    logger.info(f'✅ X投稿キュー 行{start_row}〜{end_row} に {len(new_rows)}件追加')
    return len(candidates), len(new_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='実適用（デフォルトはドライラン）')
    ap.add_argument('--ig-only', action='store_true')
    ap.add_argument('--x-only', action='store_true')
    args = ap.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    logger.info('=' * 60)
    logger.info(f'イベント → 投稿キュー展開 [{mode}]')
    logger.info('=' * 60)

    gc = gspread.service_account()
    sh = gc.open_by_key(SPREADSHEET_ID)
    today = date.today()
    logger.info(f'今日の日付: {today}')

    ig_found = ig_added = x_found = x_added = 0

    if not args.x_only:
        logger.info('\n--- IG ---')
        ig_found, ig_added = push_ig(sh, args.apply, today)

    if not args.ig_only:
        logger.info('\n--- X ---')
        x_found, x_added = push_x(sh, args.apply, today)

    logger.info('\n' + '=' * 60)
    logger.info(f'[{mode}] IG: 候補{ig_found}件 追加{ig_added}件 | X: 候補{x_found}件 追加{x_added}件')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
