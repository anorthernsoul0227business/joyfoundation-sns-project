#!/usr/bin/env python3
"""記事を破棄し、使っていた素材を「無かったこと」にする。

2026-09-30 康二郎さん:
  「記事としてはいったんばらし、知識や画像はフラットに戻し、
   かつマイナスとして記録されない仕組みが欲しい（無かった事にする）」

記事を消すだけだと、その記事のために使った画像が
  ・使用回数 +1（1回につき -2.0点、永久に残る）
  ・最終使用日（45日間はほぼ除外）
のまま拘束され、理由なく選ばれにくくなる。

    /usr/bin/python3 discard_articles.py --reason "季節が過ぎたため" --dry-run ART-0003 ART-0004
    /usr/bin/python3 discard_articles.py --reason "季節が過ぎたため" --file /tmp/nos.txt

画面の「破棄」ボタンから捨てた記事は、画像カードがこの Mac の中の
ファイルなので Web からは戻せない。見回り（run_patrol.sh）で
--release-orphans を回し、取りこぼしを拾う。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import logging
import os
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from patrol import sb

logger = logging.getLogger("discard_articles")
JST = dt.timezone(dt.timedelta(hours=9))

# 破棄しても素材を解放しない状態。すでに世に出ているものは取り消せない
KEEP_USED = {"published", "scheduled"}

# どの記事のどの画像をもう解放したかの控え。
# 見回りで何度回しても使用回数が減り続けないようにする
LEDGER = ROOT / "released_images.txt"


def _ledger_read() -> set[str]:
    if not LEDGER.exists():
        return set()
    return {l.strip() for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()}


def _ledger_add(pairs: list[str]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        for p in pairs:
            f.write(p + "\n")


def im_ids(caption: str | None) -> list[str]:
    """caption には "IM-0090 / IM-0091" のように複数入ることがある。"""
    if not caption:
        return []
    return [x.strip() for x in caption.replace("／", "/").split("/")
            if x.strip().startswith("IM-")]


def release_images(article_ids: list[str], dry_run: bool = False) -> dict:
    """その記事たちだけが使っている画像の使用実績を取り消す。

    他の記事も使っている画像は減らさない（その記事の実績は本物）。
    すでに解放済みの組み合わせは台帳で弾く。
    """
    if not article_ids:
        return {}
    mine = sb("GET", "attachments?select=caption,owner_id&owner_type=eq.article"
                     "&owner_id=in.(" + ",".join(article_ids) + ")") or []
    others = sb("GET", "attachments?select=caption,owner_id&owner_type=eq.article"
                       "&owner_id=not.in.(" + ",".join(article_ids) + ")") or []
    used_elsewhere = {im for a in others for im in im_ids(a["caption"])}

    done = _ledger_read()
    release: dict[str, str] = {}   # IM-id -> 記事のid（台帳用）
    for a in mine:
        for im in im_ids(a["caption"]):
            if im in used_elsewhere or f"{a['owner_id']} {im}" in done:
                continue
            release[im] = a["owner_id"]

    if not release or dry_run:
        return release

    import image_picker as IP
    cards = IP.load_cards()
    for im, owner in release.items():
        IP.undo_use(im, cards)
    _ledger_add([f"{owner} {im}" for im, owner in release.items()])
    return release


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("article_no", nargs="*")
    ap.add_argument("--file", help="記事番号を1行ずつ書いたファイル")
    ap.add_argument("--reason")
    ap.add_argument("--release-orphans", action="store_true",
                    help="破棄済みの記事が抱えたままの画像を解放する（見回り用）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    if args.release_orphans:
        rows = sb("GET", "articles?select=id&status=eq.discarded&limit=2000") or []
        got = release_images([r["id"] for r in rows], dry_run=args.dry_run)
        if got:
            logger.info(f"解放した画像 {len(got)}枚: {', '.join(sorted(got))}")
        else:
            logger.info("解放する画像はありませんでした。")
        return 0

    if not args.reason:
        logger.error("--reason を指定してください")
        return 1

    nos = list(args.article_no)
    if args.file:
        nos += [l.strip() for l in Path(args.file).read_text(encoding="utf-8").splitlines() if l.strip()]
    if not nos:
        logger.error("記事番号を指定してください")
        return 1

    arts = sb("GET", "articles?select=id,article_no,status,org_id,body_ai,body_final"
                     "&article_no=in.(" + ",".join(nos) + ")") or []
    found = {a["article_no"] for a in arts}
    for n in nos:
        if n not in found:
            logger.warning(f"  {n} は見つかりませんでした")

    targets = [a for a in arts if a["status"] not in KEEP_USED]
    skipped = [a for a in arts if a["status"] in KEEP_USED]
    for a in skipped:
        logger.warning(f"  {a['article_no']} は {a['status']} なのでとばします")

    if not targets:
        logger.info("破棄する記事はありません。")
        return 0

    ids = [a["id"] for a in targets]

    release = release_images(ids, dry_run=True)
    logger.info(f"破棄: {len(targets)}件 / 解放する画像: {len(release)}枚")
    for a in targets:
        logger.info(f"  {a['article_no']} ({a['status']})")
    if release:
        logger.info(f"  解放する画像: {', '.join(sorted(release))}")

    if args.dry_run:
        logger.info("--dry-run のため書き込みませんでした")
        return 0

    now = dt.datetime.now(JST).isoformat()
    for a in targets:
        sb("POST", "article_reviews", body=[{
            "org_id": a["org_id"], "article_id": a["id"],
            "decision": "request_fix",
            "note": f"出さないことにしました：{args.reason}",
            "body_snapshot": a.get("body_final") or a.get("body_ai"),
        }])
        sb("PATCH", f"articles?article_no=eq.{urllib.parse.quote(a['article_no'])}",
           {"status": "discarded", "discarded_at": now,
            "discard_reason": args.reason, "scheduled_at": None})

    got = release_images(ids)
    if got:
        logger.info(f"画像の使用実績を取り消しました: {len(got)}枚")

    logger.info(f"完了: {len(targets)}件を破棄しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
