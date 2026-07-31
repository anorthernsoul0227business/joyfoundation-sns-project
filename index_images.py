#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Drive の画像に索引を付け、Image カード（IM-）を作る。

## なぜ必要か

Drive に400枚超、ローカルに216枚あるのに、実際に投稿で使われたのは29枚だけ。
うち1枚は6回使い回され、投稿の44%が使い回し画像だった。

原因は画像が足りないことではなく、**「何が写っているか」の索引がないので選べない**こと。
原本394ファイルに出典を付けて Evidence カードにしたのと同じ構造の問題。

## 安全側の設計

- **人物が写っている画像は自動で `使用可否: 要確認` にする。** 参加者の肖像権があるため
- 企業名・製品名が読み取れる画像も `要確認`
- `使用可否: 可` でないカードは記事に使わせない（run_weekly_loop 側で制御）

実行:
    /usr/bin/python3 index_images.py --folder 済自然景色 --limit 3   # 試す
    /usr/bin/python3 index_images.py --folder 済自然景色             # 全部
    /usr/bin/python3 index_images.py --list                        # フォルダ一覧
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "knowledge" / "images"
CACHE = ROOT / "knowledge" / "_imgcache"
SA = os.path.expanduser("~/.config/gspread/service_account.json")

DESCRIBE_PROMPT = """次の画像を見て、SNS投稿の素材として使えるように索引を作ってください。

画像: {path}
元のファイル名: {name}

Read ツールでこの画像を開いて、**実際に見えるものだけ**を書いてください。
ファイル名からの推測で埋めないこと。見えないものは "不明" にしてください。

**JSONのみ**を出力してください。前後に説明を付けないこと。

```json
{{
  "内容": "何が写っているか。一文で。SNS担当者が読んで選べる具体性で",
  "被写体種別": "自然景観 | 人物あり | 機材・製品 | イベント会場 | 書籍・印刷物 | その他",
  "人物の写り込み": "なし | あり（顔が判別できる） | あり（後ろ姿・小さく写る程度）",
  "読み取れる文字": "画像内の文字（書籍タイトル・企業名・ロゴ等）。なければ空文字",
  "場所の手がかり": "地名が推測できれば。不明なら空文字",
  "色調": "全体の印象（青系・緑系・暖色・モノトーン等）",
  "向く用途": ["キーワードを3〜6個。例: 自然音, ハワイ, 海, 背景素材, 静けさ"],
  "SNS適性": "高 | 中 | 低",
  "適性の理由": "一文で。解像度・構図・被写体の魅力の観点から"
}}
```"""


def session():
    return AuthorizedSession(Credentials.from_service_account_file(
        SA, scopes=["https://www.googleapis.com/auth/drive"]))


def find_folder(sess, name: str):
    r = sess.get("https://www.googleapis.com/drive/v3/files", params={
        "q": f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        "fields": "files(id,name)"})
    fs = r.json().get("files", [])
    return fs[0]["id"] if fs else None


def list_images(sess, folder_id: str) -> list:
    r = sess.get("https://www.googleapis.com/drive/v3/files", params={
        "q": f"'{folder_id}' in parents and trashed=false and mimeType contains 'image/'",
        "fields": "files(id,name,mimeType,size,imageMediaMetadata(width,height))",
        "pageSize": 300, "orderBy": "name"})
    return r.json().get("files", [])


def download(sess, f: dict, dest: Path) -> Path:
    """縮小版をダウンロードする。Vision に渡すのに原寸は不要（8.9MBの画像もある）。"""
    dest.mkdir(parents=True, exist_ok=True)
    ext = ".jpg" if "jpeg" in f["mimeType"] or "jpg" in f["mimeType"] else ".png"
    p = dest / f"{f['id']}{ext}"
    if p.exists() and p.stat().st_size > 0:
        return p
    # thumbnailLink は縮小版を返す。大きすぎる原本を落とさずに済む
    meta = sess.get(f"https://www.googleapis.com/drive/v3/files/{f['id']}",
                    params={"fields": "thumbnailLink"}).json()
    link = meta.get("thumbnailLink")
    if link:
        # =s220 を大きめに差し替える
        link = re.sub(r"=s\d+$", "=s1600", link)
        r = sess.get(link)
        if r.status_code == 200 and len(r.content) > 1000:
            p.write_bytes(r.content)
            return p
    # サムネイルが取れない場合は原本
    r = sess.get(f"https://www.googleapis.com/drive/v3/files/{f['id']}", params={"alt": "media"})
    r.raise_for_status()
    p.write_bytes(r.content)
    return p


def describe(path: Path, name: str, timeout: int = 300) -> dict:
    proc = subprocess.run(
        ["claude", "-p", DESCRIBE_PROMPT.format(path=path, name=name), "--output-format", "text"],
        capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    if proc.returncode != 0:
        raise RuntimeError(f"claude 実行失敗: {proc.stderr[:200]}")
    out = proc.stdout
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", out, re.S) or re.search(r"(\{.*\})", out, re.S)
    if not m:
        raise ValueError(f"JSON抽出失敗: {out[:200]}")
    return json.loads(m.group(1))


def next_id() -> int:
    CARDS.mkdir(parents=True, exist_ok=True)
    ns = [int(m.group(1)) for p in CARDS.glob("IM-*.md")
          for m in [re.match(r"IM-(\d+)", p.name)] if m]
    return max(ns) + 1 if ns else 1


def write_card(n: int, f: dict, folder: str, d: dict) -> Path:
    md = f.get("imageMediaMetadata") or {}
    # 人物が写る・文字が読み取れるものは自動で要確認にする（肖像権・企業名）
    person = d.get("人物の写り込み", "")
    text_in = (d.get("読み取れる文字") or "").strip()
    if person.startswith("あり"):
        ok, why = "要確認", "人物が写っているため、肖像権・公開許諾の確認が必要"
    elif text_in and d.get("被写体種別") != "書籍・印刷物":
        ok, why = "要確認", f"画像内に文字（{text_in[:30]}）があり、企業名・製品名の可能性"
    else:
        ok, why = "可", ""

    body = f"""---
id: IM-{n:04d}
drive_id: {f['id']}
filename: {f['name']}
folder: {folder}
寸法: {md.get('width','?')}x{md.get('height','?')}
サイズ: {int(f.get('size',0))/1e6:.1f}MB

内容: {d.get('内容','')}
被写体種別: {d.get('被写体種別','')}
人物の写り込み: {person}
読み取れる文字: {text_in}
場所の手がかり: {d.get('場所の手がかり','')}
色調: {d.get('色調','')}
向く用途: [{', '.join(d.get('向く用途', []))}]
SNS適性: {d.get('SNS適性','')}
適性の理由: {d.get('適性の理由','')}

使用可否: {ok}
要確認の理由: {why}
確認者: null
確認日: null
使用回数: 0
最終使用日: null

status: draft
indexed_at: {date.today().isoformat()}
---
"""
    p = CARDS / f"IM-{n:04d}.md"
    p.write_text(body, encoding="utf-8")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", help="Drive のフォルダ名")
    ap.add_argument("--limit", type=int, help="処理する枚数の上限（試験用）")
    ap.add_argument("--list", action="store_true", help="対象フォルダの候補を表示")
    args = ap.parse_args()

    sess = session()

    if args.list or not args.folder:
        r = sess.get("https://www.googleapis.com/drive/v3/files", params={
            "q": "mimeType='application/vnd.google-apps.folder' and trashed=false",
            "fields": "files(id,name)", "pageSize": 100})
        print("アクセスできるフォルダ:")
        for f in sorted(r.json().get("files", []), key=lambda x: x["name"]):
            n = len(list_images(sess, f["id"]))
            if n:
                print(f"  {f['name'][:44]:44} {n:3}枚")
        return 0

    fid = find_folder(sess, args.folder)
    if not fid:
        print(f"フォルダが見つかりません: {args.folder}")
        return 1

    imgs = list_images(sess, fid)
    if args.limit:
        imgs = imgs[:args.limit]
    print(f"{args.folder}: {len(imgs)}枚を処理します\n")

    # 既にカード化済みの drive_id は飛ばす
    done = set()
    CARDS.mkdir(parents=True, exist_ok=True)
    for p in CARDS.glob("IM-*.md"):
        m = re.search(r"^drive_id:\s*(\S+)", p.read_text(encoding="utf-8"), re.M)
        if m:
            done.add(m.group(1))

    n = next_id()
    made = skipped = failed = 0
    for f in imgs:
        if f["id"] in done:
            skipped += 1
            continue
        try:
            path = download(sess, f, CACHE)
            d = describe(path, f["name"])
            card = write_card(n, f, args.folder, d)
            # フィールド名「要確認の理由」に誤ヒットしないよう、値だけを見る
            m = re.search(r"^使用可否:\s*(\S+)", card.read_text(encoding="utf-8"), re.M)
            mark = "⚠" if m and m.group(1) == "要確認" else "○"
            print(f"  {mark} {card.name}  {d.get('SNS適性','?')}  {d.get('内容','')[:44]}")
            n += 1
            made += 1
        except Exception as e:
            print(f"  ✗ {f['name'][:40]}: {type(e).__name__}: {str(e)[:70]}")
            failed += 1

    print(f"\n作成 {made}件 / 既存スキップ {skipped}件 / 失敗 {failed}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
