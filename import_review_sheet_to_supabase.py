#!/usr/bin/env python3
"""週次_レビュー シートの記事を Supabase の articles / attachments に取り込む。

共有ボード（sns-calendar-app /board）へ移行するための一回きりの取り込み。
同じ記事ID（article_no）があれば上書きするので、何度実行しても増えない。

使い方:
  set -a; source ~/.config/jf/supabase.env; set +a
  ./import_review_sheet_to_supabase.py            # 取り込む
  ./import_review_sheet_to_supabase.py --dry-run  # TSV を作るだけ

DB 接続は psql に任せる（psycopg が無いため）。PGPASSWORD は SUPABASE_SECRET_KEY
（= DB パスワード。2026-09-02 に康二郎さんが Reset password で発行）を使う。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import gspread

SPREADSHEET_KEY = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
TAB_REVIEW = "週次_レビュー"
TEST_BANNER = "【ループ検証テスト・投稿しないでください】"

PLATFORM = {"X": "x", "Instagram": "ig", "note": "note", "YouTube": "youtube", "LINE": "line"}
STATUS = {
    "AI下書き": "ai_draft",
    "要確認あり": "needs_check",
    "康二郎OK": "staff_ok",
    "圭一郎OK": "approved",
    "要修正": "needs_fix",
    "投稿予約": "scheduled",
    "投稿済": "published",
}
APPLY = {"恒久ルールにする": "permanent", "今回限り": "once", "不要": "none"}

PSQL = "/opt/homebrew/opt/postgresql@16/bin/psql"
CONN = ("host=db.msghvqclexpvgkrctxug.supabase.co port=5432 dbname=postgres "
        "user=postgres sslmode=require connect_timeout=15")


def copy_escape(v: str) -> str:
    """COPY ... FORMAT text 用のエスケープ。

    csv モジュールの escapechar は「エスケープ文字そのもの」も二重化するため、
    改行が \\n（バックスラッシュ2つ）になり、DB に \\n という文字列が残っていた。
    2026-09-02 に発覚。COPY text の仕様どおり、ここで自分でエスケープする。
    """
    return (v.replace("\\", "\\\\")
             .replace("\t", "\\t")
             .replace("\n", "\\n")
             .replace("\r", "\\r"))


def write_tsv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        for row in rows:
            f.write("\t".join(copy_escape(str(row[c])) for c in cols) + "\n")


def pg_array(items: list[str]) -> str:
    return "{" + ",".join('"' + i.replace('"', '\\"') + '"' for i in items) + "}"


def title_of(body: str) -> str:
    """本文の最初の【見出し】、無ければ最初の行を一覧用の題にする。"""
    m = re.search(r"【([^】]{2,40})】", body)
    if m and TEST_BANNER not in m.group(0):
        return m.group(1)
    for line in body.splitlines():
        line = line.strip()
        if line and line != TEST_BANNER:
            return line[:40]
    return ""


def drive_id(url: str) -> str | None:
    m = re.search(r"/d/([A-Za-z0-9_-]{10,})", url)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-test-prefix", action="store_true",
                    help="記事IDの TEST- を残す（既定では外す。全記事が --test-cards 生成のため）")
    args = ap.parse_args()

    gc = gspread.service_account()
    ws = gc.open_by_key(SPREADSHEET_KEY).worksheet(TAB_REVIEW)
    # 画像プレビュー列は =IMAGE("url") なので数式のまま読む
    rows = ws.get_all_values(value_render_option="FORMULA")
    header, data = rows[0], [r for r in rows[1:] if r and r[0].strip()]
    assert header[0] == "記事ID" and header[6] == "AI原稿", header

    def col(r, i):
        return r[i].strip() if len(r) > i else ""

    articles, images = [], []
    # 2026-09-02: シート上で ART-0040 が2件（8/17 note と 8/19 X）に重複していた。
    # publish() の採番が行数から計算しているため、行を消すと同じ番号が再発行される。
    # 取り込み側では 2件目以降に -2, -3 を付けて区別する。
    seen: dict[str, int] = {}
    for r in data:
        aid = col(r, 0)
        if not args.keep_test_prefix:
            aid = aid.replace("TEST-", "", 1)
        seen[aid] = seen.get(aid, 0) + 1
        if seen[aid] > 1:
            print(f"!! 記事IDが重複: {aid} → {aid}-{seen[aid]} として取り込みます")
            aid = f"{aid}-{seen[aid]}"
        body_ai = col(r, 6).replace(TEST_BANNER, "").strip()
        status = STATUS.get(col(r, 7), "ai_draft")
        # 列I「修正版（ここに直接お書きください）」は名前に反して、圭一郎さんが
        # 直した本文ではなく「こう直してほしい」という指示を書く欄として使われている。
        # 2026-09-02: これを body_final（＝確定した本文）に入れてしまい、
        # ボードが本文の代わりに指示文を表示していた。指示は fix_note に入れる。
        body_final = col(r, 12) or ""
        fix_note = "\n\n".join(c for c in (col(r, 8), col(r, 10)) if c)
        if fix_note:
            status = "needs_fix"
        elif status == "needs_fix":
            fix_note = "（理由の記載なし）"
        stamp = col(r, 13)
        try:
            ts = datetime.strptime(stamp, "%Y-%m-%d %H:%M").isoformat()
        except ValueError:
            ts = ""
        articles.append({
            "article_no": aid,
            "week": col(r, 1),
            "platform": PLATFORM.get(col(r, 2), "x"),
            "scheduled_date": col(r, 3),
            "grade": (col(r, 4)[:1] if col(r, 4)[:1] in "ABC" else ""),
            "source_card_ids": pg_array([c.strip() for c in col(r, 5).split(",") if c.strip()]),
            "title": title_of(body_ai),
            "body_ai": body_ai,
            "body_final": body_final,
            "status": status,
            "fix_note": fix_note,
            "fix_type": col(r, 9)[:2] if col(r, 9) else "",
            "fix_apply": APPLY.get(col(r, 11), ""),
            "image_reason": col(r, 17),
            "created_at": ts,
        })
        m = re.match(r'=IMAGE\("([^"]+)"\)', col(r, 14))
        if m:
            images.append({
                "article_no": aid,
                "public_url": m.group(1),
                "drive_file_id": drive_id(col(r, 16)) or "",
                "caption": col(r, 15),
            })

    tmp = Path(tempfile.mkdtemp(prefix="jf-import-"))
    a_tsv, i_tsv = tmp / "articles.tsv", tmp / "images.tsv"
    a_cols = list(articles[0].keys())
    i_cols = ["article_no", "public_url", "drive_file_id", "caption"]
    write_tsv(a_tsv, a_cols, articles)
    write_tsv(i_tsv, i_cols, images)
    print(f"記事 {len(articles)} 件、画像 {len(images)} 件 → {tmp}")
    if args.dry_run:
        return 0

    sql = f"""
    \\set ON_ERROR_STOP on
    BEGIN;
    CREATE TEMP TABLE imp_articles (
      article_no text, week text, platform text, scheduled_date text, grade text,
      source_card_ids text, title text, body_ai text, body_final text, status text,
      fix_note text, fix_type text, fix_apply text, image_reason text, created_at text
    );
    \\copy imp_articles FROM '{a_tsv}' WITH (FORMAT text)
    CREATE TEMP TABLE imp_images (article_no text, public_url text, drive_file_id text, caption text);
    \\copy imp_images FROM '{i_tsv}' WITH (FORMAT text)

    -- 組織は1つだけ（康二郎さんの Workspace）。複数になったら明示指定に変える
    CREATE TEMP TABLE the_org AS SELECT id FROM public.organizations ORDER BY created_at LIMIT 1;

    INSERT INTO public.articles (org_id, article_no, week, platform, scheduled_date, grade,
      source_card_ids, title, body_ai, body_final, status, fix_note, fix_type, fix_apply,
      image_reason, created_at)
    SELECT o.id, i.article_no, NULLIF(i.week,''), i.platform,
      NULLIF(i.scheduled_date,'')::date, NULLIF(i.grade,''),
      i.source_card_ids::text[], i.title, i.body_ai, NULLIF(i.body_final,''), i.status,
      NULLIF(i.fix_note,''), NULLIF(i.fix_type,''), NULLIF(i.fix_apply,''),
      NULLIF(i.image_reason,''), COALESCE(NULLIF(i.created_at,'')::timestamptz, now())
    FROM imp_articles i, the_org o
    ON CONFLICT (org_id, article_no) DO UPDATE SET
      week = EXCLUDED.week, platform = EXCLUDED.platform, grade = EXCLUDED.grade,
      source_card_ids = EXCLUDED.source_card_ids, title = EXCLUDED.title,
      body_ai = EXCLUDED.body_ai,
      -- ボード側で圭一郎さんが判断済みのものは、シートの古い状態で上書きしない
      body_final = COALESCE(articles.body_final, EXCLUDED.body_final),
      status = CASE WHEN articles.reviewed_at IS NULL THEN EXCLUDED.status ELSE articles.status END,
      fix_note = CASE WHEN articles.reviewed_at IS NULL THEN EXCLUDED.fix_note ELSE articles.fix_note END,
      image_reason = EXCLUDED.image_reason;

    DELETE FROM public.attachments a USING public.articles ar, the_org o
      WHERE a.owner_type = 'article' AND a.owner_id = ar.id AND ar.org_id = o.id
        AND ar.article_no IN (SELECT article_no FROM imp_images);
    INSERT INTO public.attachments (org_id, owner_type, owner_id, storage_path, public_url,
      mime_type, sort_order, caption, drive_file_id)
    SELECT o.id, 'article', ar.id, 'drive/' || COALESCE(NULLIF(i.drive_file_id,''), i.caption),
      i.public_url, 'image/jpeg', 0, NULLIF(i.caption,''), NULLIF(i.drive_file_id,'')
    FROM imp_images i JOIN the_org o ON true
    JOIN public.articles ar ON ar.org_id = o.id AND ar.article_no = i.article_no;

    SELECT status, count(*) FROM public.articles GROUP BY 1 ORDER BY 1;
    SELECT count(*) AS attachments FROM public.attachments WHERE owner_type = 'article';
    COMMIT;
    """
    env = dict(os.environ)
    pw = env.get("SUPABASE_SECRET_KEY") or env.get("PGPASSWORD")
    if not pw:
        print("SUPABASE_SECRET_KEY（DBパスワード）が環境変数にありません", file=sys.stderr)
        return 2
    env["PGPASSWORD"] = pw
    res = subprocess.run([PSQL, CONN, "-q", "-A"], input=sql, text=True, env=env)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
