#!/usr/bin/env python3
"""圭一郎さんに一通だけメールを送る。

毎週のお知らせ（notify_owner.py）とは別に、画面を変えたときなどの
お知らせを送るために使う。宛先・差出人は .env のものをそのまま使う。

    /usr/bin/python3 send_mail.py --subject "..." --body-file mail.txt --dry-run
    /usr/bin/python3 send_mail.py --subject "..." --body-file mail.txt
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger("send_mail")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--to", help="指定しなければ .env の OWNER_NOTIFY_TO")
    ap.add_argument("--dry-run", action="store_true", help="送らずに中身だけ出す")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    body = Path(args.body_file).read_text(encoding="utf-8")
    to = args.to or os.getenv("OWNER_NOTIFY_TO", "").strip() or os.getenv("NOTIFY_GMAIL_TO", "").strip()
    sender = os.getenv("NOTIFY_GMAIL_USER", "")
    if not to:
        logger.error("宛先がありません（OWNER_NOTIFY_TO / NOTIFY_GMAIL_TO）")
        return 1

    print("=" * 60)
    print(f"差出人: {sender}")
    print(f"宛先  : {to}")
    print(f"件名  : {args.subject}")
    print("=" * 60)
    print(body)
    print("=" * 60)

    if args.dry_run:
        logger.info("--dry-run のため送っていません")
        return 0

    from notifier import GmailChannel
    ch = GmailChannel(
        sender=sender,
        app_password=os.getenv("NOTIFY_GMAIL_APP_PASSWORD", ""),
        recipients=[to],
        display_name="ジョイファンデーション 共有ボード",
    )
    if not ch.send(args.subject, body):
        logger.error("送れませんでした")
        return 1
    logger.info(f"送りました → {to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
