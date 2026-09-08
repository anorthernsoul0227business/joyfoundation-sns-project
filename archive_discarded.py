#!/usr/bin/env python3
"""破棄して1週間たった記事を、アプリの一覧から外す。

2026-09-08 康二郎さんの方針:
  ・破棄したものは1週間ほど残し、時間が過ぎたらアプリから消してよい
  ・ただし元データは残す

消すのはその記事専用の画像だけ。Drive の写真は画像プール（482枚）を
複数の記事で使い回しているので消してはいけない。

    /usr/bin/python3 archive_discarded.py --dry-run
    /usr/bin/python3 archive_discarded.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from patrol import sb

logger = logging.getLogger("archive_discarded")
JST = dt.timezone(dt.timedelta(hours=9))
KEEP_DAYS = 7


def delete_r2_object(key: str) -> bool:
    """R2 のオブジェクトを消す。設定が無ければ何もしない。"""
    try:
        import boto3
    except ImportError:
        return False
    acct = os.getenv("R2_ACCOUNT_ID")
    if not acct:
        return False
    s3 = boto3.client(
        "s3", endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"), region_name="auto")
    s3.delete_object(Bucket=os.getenv("R2_BUCKET_NAME"), Key=key)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    cutoff = (dt.datetime.now(JST) - dt.timedelta(days=KEEP_DAYS)).isoformat()
    targets = sb("GET", "articles?select=id,article_no,discard_reason,discarded_at"
                        f"&status=eq.discarded&archived_at=is.null"
                        f"&discarded_at=lt.{urllib.parse.quote(cutoff)}") or []
    if not targets:
        logger.info(f"{KEEP_DAYS}日を過ぎた破棄記事はありません。")
        return 0
    logger.info(f"{len(targets)}件をアプリの一覧から外します（データは残します）")

    removed = 0
    for a in targets:
        atts = sb("GET", "attachments?select=id,storage_path&owner_type=eq.article"
                         f"&owner_id=eq.{a['id']}") or []
        for at in atts:
            path = at["storage_path"] or ""
            # Drive の写真は画像プールを使い回しているので消さない
            if path.startswith("drive/"):
                continue
            if args.dry_run:
                logger.info(f"  {a['article_no']}: 専用画像を消します {path}")
                continue
            try:
                delete_r2_object(path)
                sb("DELETE", f"attachments?id=eq.{at['id']}")
                removed += 1
            except Exception as e:
                logger.warning(f"  {a['article_no']}: 画像を消せませんでした {type(e).__name__}")
        if not args.dry_run:
            sb("PATCH", f"articles?id=eq.{a['id']}",
               {"archived_at": dt.datetime.now(JST).isoformat()})
        logger.info(f"  {a['article_no']}（{a.get('discard_reason') or '理由なし'}）")

    logger.info(f"完了: {len(targets)}件を一覧から外し、専用画像 {removed}件を消しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
