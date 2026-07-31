#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""投稿の反応データを取得して「反応データ」タブへ記録する。

## なぜ必要か

投稿の反応を見ずに記事を作り続けても「読まれ方」は改善しない。
ただし週3本では統計的にほぼ何も言えないため、**自動学習の教師には使わない**。
月次で人が仮説を立てるための材料として蓄積する（INSIGHT カード方式）。

## 取得期限に注意

X の非公開メトリクス（プロフィールクリック等）は取得可能期間に制限がある（概ね直近30日）。
公開メトリクス（impression_count 等）は期限がないため、まず公開分を確保する。

## 測定窓

「いつか取った値」は投稿間で比較できない。投稿からの経過日数を必ず記録し、
分析時に近い窓どうしで比較する（目安: 72時間 / 14日）。

実行:
    /usr/bin/python3 collect_metrics.py            # X と Instagram の両方
    /usr/bin/python3 collect_metrics.py --x-only
    /usr/bin/python3 collect_metrics.py --dry-run  # 取得だけしてシートに書かない
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import gspread

ROOT = Path(__file__).resolve().parent
SPREADSHEET_KEY = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
TAB_METRICS = "反応データ"

HEADER = [
    "媒体", "投稿ID", "投稿日時", "取得日時", "経過日数",
    "インプレッション/リーチ", "いいね", "リポスト/シェア", "返信", "保存",
    "本文冒頭", "取得エラー",
]


def load_env() -> dict:
    return dict(re.findall(r"^([A-Z_]+)=(.*)$", (ROOT / ".env").read_text(encoding="utf-8"), re.M))


def posts_from_sheet(sh, tab: str) -> list:
    """投稿キューから (投稿ID, 投稿日時, 本文冒頭) を拾う。IDはメモ欄に記録されている。"""
    try:
        rows = sh.worksheet(tab).get_all_values()
    except gspread.WorksheetNotFound:
        return []
    hdr = rows[0]
    if "メモ" not in hdr:
        return []
    mi = hdr.index("メモ")
    ti = hdr.index("投稿日時") if "投稿日時" in hdr else 0
    bi = 1
    out = []
    for r in rows[1:]:
        if len(r) <= mi:
            continue
        m = re.search(r"ID:(\d+)", r[mi])
        if m:
            out.append((m.group(1), r[ti] if len(r) > ti else "",
                        (r[bi] if len(r) > bi else "").replace("\n", " ")[:40]))
    return out


def days_since(posted: str, now: datetime) -> str:
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return str((now - datetime.strptime(posted.strip(), fmt)).days)
        except ValueError:
            continue
    return ""


def fetch_x(env: dict, posts: list, now: datetime) -> list:
    """X の公開メトリクスを取得する。25件ずつまとめて問い合わせる。"""
    from requests_oauthlib import OAuth1Session
    oauth = OAuth1Session(
        env["X_CONSUMER_KEY"], client_secret=env["X_CONSUMER_SECRET"],
        resource_owner_key=env["X_ACCESS_TOKEN"], resource_owner_secret=env["X_ACCESS_TOKEN_SECRET"])

    meta = {p[0]: p for p in posts}
    rows = []
    for i in range(0, len(posts), 25):
        ids = [p[0] for p in posts[i:i + 25]]
        r = oauth.get("https://api.x.com/2/tweets",
                      params={"ids": ",".join(ids), "tweet.fields": "public_metrics,created_at"})
        if r.status_code != 200:
            for pid in ids:
                p = meta[pid]
                rows.append(["X", pid, p[1], now.strftime("%Y-%m-%d %H:%M"),
                             days_since(p[1], now), "", "", "", "", "", p[2],
                             f"HTTP {r.status_code}"])
            continue
        body = r.json()
        got = {t["id"]: t for t in body.get("data", [])}
        for pid in ids:
            p = meta[pid]
            t = got.get(pid)
            if not t:
                # 削除済み・非公開など。errors に理由が入る
                err = next((e.get("detail", "取得不可")[:40] for e in body.get("errors", [])
                            if e.get("value") == pid), "取得不可")
                rows.append(["X", pid, p[1], now.strftime("%Y-%m-%d %H:%M"),
                             days_since(p[1], now), "", "", "", "", "", p[2], err])
                continue
            m = t["public_metrics"]
            rows.append([
                "X", pid, p[1], now.strftime("%Y-%m-%d %H:%M"), days_since(p[1], now),
                m.get("impression_count", ""), m.get("like_count", ""),
                m.get("retweet_count", ""), m.get("reply_count", ""),
                m.get("bookmark_count", ""), p[2], "",
            ])
    return rows


def fetch_ig(env: dict, posts: list, now: datetime) -> list:
    """Instagram のインサイトを取得する。1件ずつしか取れない。"""
    import requests
    token = env.get("IG_LONG_LIVED_TOKEN") or env.get("IG_ACCESS_TOKEN")
    rows = []
    for pid, posted, head in posts:
        base = ["Instagram", pid, posted, now.strftime("%Y-%m-%d %H:%M"), days_since(posted, now)]
        try:
            r = requests.get(
                f"https://graph.facebook.com/v21.0/{pid}/insights",
                params={"metric": "reach,likes,shares,comments,saved", "access_token": token},
                timeout=30)
            if r.status_code != 200:
                msg = (r.json().get("error", {}) or {}).get("message", "")[:60]
                rows.append(base + ["", "", "", "", "", head, f"HTTP {r.status_code} {msg}"])
                continue
            v = {d["name"]: d["values"][0].get("value", "") for d in r.json().get("data", [])}
            rows.append(base + [v.get("reach", ""), v.get("likes", ""), v.get("shares", ""),
                                v.get("comments", ""), v.get("saved", ""), head, ""])
        except Exception as e:
            rows.append(base + ["", "", "", "", "", head, f"{type(e).__name__}: {str(e)[:40]}"])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--x-only", action="store_true")
    ap.add_argument("--ig-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="シートに書き込まない")
    args = ap.parse_args()

    env = load_env()
    gc = gspread.service_account()
    sh = gc.open_by_key(SPREADSHEET_KEY)
    now = datetime.now()

    rows = []
    if not args.ig_only:
        xp = posts_from_sheet(sh, "X投稿キュー")
        print(f"X: {len(xp)}件のIDを検出")
        if xp:
            rows += fetch_x(env, xp, now)
    if not args.x_only:
        ip = posts_from_sheet(sh, "IG投稿キュー")
        print(f"Instagram: {len(ip)}件のIDを検出")
        if ip:
            rows += fetch_ig(env, ip, now)

    ok = [r for r in rows if not r[-1]]
    ng = [r for r in rows if r[-1]]
    print(f"\n取得成功 {len(ok)}件 / 失敗 {len(ng)}件")
    for r in ng[:5]:
        print(f"  ✗ {r[0]} {r[1]}: {r[-1]}")
    if len(ng) > 5:
        print(f"  （他 {len(ng)-5}件）")

    if args.dry_run:
        print("\n--dry-run のためシートには書き込みません")
        return 0

    try:
        ws = sh.worksheet(TAB_METRICS)
        existing = ws.get_all_values()
        start = len(existing) + 1 if len(existing) > 1 else 2
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=TAB_METRICS, rows=2000, cols=len(HEADER))
        ws.update(values=[HEADER], range_name="A1")
        ws.freeze(rows=1)
        # 圭一郎さんに見せる必要はないので非表示にしておく
        sh.batch_update({"requests": [{"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "hidden": True}, "fields": "hidden"}}]})
        start = 2
        print(f"タブ『{TAB_METRICS}』を作成しました（非表示）")

    ws.update(values=rows, range_name=f"A{start}")
    print(f"『{TAB_METRICS}』に {len(rows)}行を追記しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
