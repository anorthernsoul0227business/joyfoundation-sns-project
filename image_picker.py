#!/usr/bin/env python3
"""記事に添える画像を選ぶ。

これまで画像は週次ループの外にあり、記事だけが生成されていた。
Instagram は画像が主・文が従なので、画像が付かないと投稿として成立しない。

実測では Drive に400枚以上あるのに29枚しか使われていなかった。
同じ画像の使い回しを避けることが、この仕組みの主目的のひとつ。

選び方は決め打ちの点数計算にしてある。LLM に選ばせる案もあったが、
生成が既に十数分かかっており、これ以上待ち時間を増やしたくない。
理由を人が読んで納得できることも重視した（なぜその画像なのかが説明できる）。

    /usr/bin/python3 image_picker.py --dry-run "記事の本文" --media Instagram
"""

import argparse
import io
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMGDIR = ROOT / "knowledge" / "images"
CACHE = ROOT / "knowledge" / "_imgcache"
SA = os.path.expanduser("~/.config/gspread/service_account.json")

# 媒体ごとの枚数。Instagram はカルーセルを想定して複数、X と note は1枚。
COUNT = {"Instagram": 3, "X": 1, "note": 1}

# 直近この日数に使った画像は選ばない（使い回し防止の主装置）
COOLDOWN_DAYS = 45

STOP = set("こと もの ため よう そう これ それ ある いる する なる れる られる "
           "ます です ました ません また しかし ただ そして では には".split())


# --------------------------------------------------------------------------
# カードの読み書き
# --------------------------------------------------------------------------

def _field(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


# 編集ルールによる足切り。カード側の「使用可否」だけに頼ると、
# ルールが後から増えたときに既存カードが取り残される（実際 RULE-0008 の制定前に
# 索引化した書影12枚が「可」のまま残り、2026-08-17 に note の記事へ選ばれた）。
BANNED_SUBJECTS = ("書籍", "印刷物", "書影")           # RULE-0008
BANNED_IN_TEXT = ("効く", "治る", "改善", "解消", "効果",  # RULE-0001 / 0008
                  "%", "％", "有効率")


def _blocked_by_rule(t: str) -> str:
    """編集ルールに触れる画像なら、理由を返す。"""
    subject = _field(t, "被写体種別")
    if any(w in subject for w in BANNED_SUBJECTS):
        return "RULE-0008: 書影は惹句が読める形では使わない"
    ocr = _field(t, "読み取れる文字")
    hit = [w for w in BANNED_IN_TEXT if w in ocr]
    if hit:
        return f"RULE-0001: 写り込んだ文字に効果の断言（{'・'.join(hit)}）"
    return ""


def load_cards(explain: bool = False) -> list:
    """IM カードを読む。使用可否が「可」でないもの、編集ルールに触れるものを外す。"""
    cards, dropped = [], []
    for p in sorted(IMGDIR.glob("IM-*.md")):
        t = p.read_text(encoding="utf-8")
        usable = _field(t, "使用可否")
        if usable and usable != "可":
            dropped.append((_field(t, "id"), f"使用可否={usable}"))
            continue
        rule = _blocked_by_rule(t)
        if rule:
            dropped.append((_field(t, "id"), rule))
            continue
        raw_uses = _field(t, "向く用途")
        tags = [w.strip() for w in re.sub(r"^\[|\]$", "", raw_uses).split(",") if w.strip()]
        used_at = _field(t, "最終使用日")
        try:
            count = int(_field(t, "使用回数") or 0)
        except ValueError:
            count = 0
        cards.append({
            "path": p,
            "id": _field(t, "id"),
            "drive_id": _field(t, "drive_id"),
            "filename": _field(t, "filename"),
            "内容": _field(t, "内容"),
            "被写体種別": _field(t, "被写体種別"),
            "人物": _field(t, "人物の写り込み"),
            "文字": _field(t, "読み取れる文字"),
            "色調": _field(t, "色調"),
            "場面": _field(t, "場面"),
            "場面種別": _field(t, "場面種別"),
            "汎用性": _field(t, "汎用性"),
            "汎用性の理由": _field(t, "汎用性の理由"),
            "tags": tags,
            "適性": _field(t, "SNS適性"),
            "理由": _field(t, "適性の理由"),
            "使用回数": count,
            "最終使用日": None if used_at in ("", "null") else used_at,
            "r2_url": _field(t, "r2_url"),
        })
    if explain and dropped:
        print(f"除外 {len(dropped)}枚:")
        for cid, why in dropped:
            print(f"  {cid}  {why}")
    return cards


def save_field(card: dict, key: str, value: str) -> None:
    """カードの1項目を書き換える。無ければ status 行の前に足す。"""
    p = card["path"]
    t = p.read_text(encoding="utf-8")
    if re.search(rf"^{re.escape(key)}:", t, re.M):
        t = re.sub(rf"^{re.escape(key)}:.*$", f"{key}: {value}", t, count=1, flags=re.M)
    else:
        t = re.sub(r"^status:", f"{key}: {value}\nstatus:", t, count=1, flags=re.M)
    p.write_text(t, encoding="utf-8")
    card[key] = value


# --------------------------------------------------------------------------
# 選ぶ
# --------------------------------------------------------------------------

def words(text: str) -> set:
    t = unicodedata.normalize("NFKC", text)
    got = set(re.findall(r"[ぁ-んァ-ヴ一-龥]{2,}|[A-Za-z]{3,}", t))
    return {w for w in got if w not in STOP}


def score(card: dict, topic: set, today: date,
          for_event: bool = False, recent_kinds: list = None) -> tuple:
    """点数と、その内訳（人に見せる理由）を返す。

    for_event:
        イベント告知の記事かどうか。告知なら、研修や催しの写真こそ適切なので
        「汎用性が低い」ことを減点しない。
    recent_kinds:
        直近の記事で使った場面種別。同じ種別が続かないよう軽く減点する。
    """
    reasons = []
    s = 0.0

    # 記事と画像の言葉の重なり。タグは意図して付けた語なので重く見る
    tag_hit = {w for w in card["tags"] if any(w in t or t in w for t in topic)}
    body_hit = words(card["内容"]) & topic
    s += 3.0 * len(tag_hit) + 1.0 * len(body_hit)
    if tag_hit:
        reasons.append("用途が一致: " + "・".join(sorted(tag_hit)))
    elif body_hit:
        reasons.append("内容が一致: " + "・".join(sorted(list(body_hit)[:3])))

    # 写真としての質
    s += {"高": 4.0, "中": 1.5, "低": -2.0}.get(card["適性"], 0.0)

    # 使い回しを避ける。ここが効かないと同じ写真ばかりになる
    s -= 2.0 * card["使用回数"]
    if card["最終使用日"]:
        try:
            days = (today - date.fromisoformat(card["最終使用日"])).days
            if days < COOLDOWN_DAYS:
                s -= 100.0            # 実質除外
                reasons.append(f"{days}日前に使用済み")
        except ValueError:
            pass
    if card["使用回数"] == 0:
        s += 1.5
        reasons.append("未使用")

    # 汎用性。特定の催しの写真を平常の投稿に使うと、過去の催しを今のことのように
    # 見せてしまう。イベント告知記事なら別だが、それは呼び出し側で判断する。
    # 2026-09-04: 「同じような写真ばかり」の原因がここだった。
    # 汎用性=低 の -6.0 が効きすぎて、研修・講座（27枚）と特定イベント（15枚）が
    # 一度も選ばれていなかった。一方 日常・風景 は 適性=高・汎用性=高 で
    # 素点 8.0 を取り、上位を占め続けていた。
    # 2026-08-17 に人物の減点をやめたのと同じ問題が、別の経路で再発していた。
    kind = card["場面種別"] or ""
    if for_event:
        # 告知記事では、その催しの様子が写っている方がふさわしい
        s += {"高": 1.0, "中": 1.0, "低": 1.5}.get(card["汎用性"], 0.0)
        if kind in ("研修・講座", "特定イベント", "施術・体験"):
            s += 3.0
            reasons.append(f"催しの様子が伝わる（{kind}）")
    else:
        s += {"高": 3.0, "中": 0.5, "低": -2.5}.get(card["汎用性"], 0.0)
        if card["汎用性"] == "低":
            reasons.append(f"特定の場面に限られる（{kind or '?'}）")

    # 直近で使った種別が続くと「同じような写真」に見える。
    # 直近ほど強く避ける（1つ前 -3.0、2つ前 -2.0、3つ前 -1.0）
    for i, k in enumerate(recent_kinds or []):
        if k and k == kind:
            s -= max(0.0, 3.0 - i)
            reasons.append(f"直前に同じ種別を使用（{kind}）")
            break
    if card["場面"]:
        reasons.append(f"場面: {card['場面'][:34]}")

    # 人物は 2026-08-17 に減点をやめた。協会の活動写真は人が写るものが本体であり、
    # 減点すると風景ばかりになって「何をしている団体か」が伝わらない。
    if card["文字"]:
        s -= 0.5

    return s, reasons


def pick(text: str, media: str, cards: list, today: date = None, k: int = None,
         for_event: bool = False, recent_kinds: list = None) -> list:
    """記事に合う画像を選ぶ。色調をばらけさせて、並べたときの統一感を崩さない。"""
    today = today or date.today()
    k = k or COUNT.get(media, 1)
    topic = words(text)

    ranked = []
    for c in cards:
        s, why = score(c, topic, today, for_event, recent_kinds)
        if s <= -50:                  # クールダウン中は候補にしない
            continue
        ranked.append((s, why, c))
    ranked.sort(key=lambda x: -x[0])

    chosen, seen_tone, seen_kind = [], set(), set()
    for s, why, c in ranked:
        if len(chosen) >= k:
            break
        # 同じ色調・同じ種別ばかりにならないよう、2枚目以降は一度ずらす
        tone = (c["色調"] or "")[:6]
        kind = c["場面種別"] or ""
        if len(chosen) and len(ranked) > k * 2 and (tone in seen_tone or kind in seen_kind):
            continue
        seen_tone.add(tone)
        seen_kind.add(kind)
        chosen.append({**c, "score": round(s, 1), "why": "／".join(why) or "候補内で最上位"})
    # ずらした結果 k 枚に満たない場合は素直に上から埋める
    for s, why, c in ranked:
        if len(chosen) >= k:
            break
        if any(x["id"] == c["id"] for x in chosen):
            continue
        chosen.append({**c, "score": round(s, 1), "why": "／".join(why) or "候補内で最上位"})
    return chosen


# --------------------------------------------------------------------------
# 公開URL（R2）
# --------------------------------------------------------------------------

def preview_url(card: dict) -> str:
    """シートのプレビュー用URL。

    Drive のサムネイルは認証なしで画像本体を返すため、=IMAGE() で表示できる。

    2026-09-04 追記: 「R2 の公開URLは 403 を返す」としてここで Drive を使ってきたが、
    誤診だった。403 の中身は Cloudflare のエラーコード 1010 で、公開設定ではなく
    Python の User-Agent をボットとみなした遮断。ブラウザの UA を付けると 200 が返る。
    ブラウザ表示は R2 でも問題ないため、今後は R2 の公開URLへ寄せていく。
    ただし過去の記事の画像は Drive を指しているので、この関数はそのまま残す。
    """
    return f"https://drive.google.com/thumbnail?id={card['drive_id']}&sz=w800"


def open_url(card: dict) -> str:
    """人がクリックして原寸を見るためのURL。"""
    return f"https://drive.google.com/file/d/{card['drive_id']}/view"


def _drive_session():
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2.service_account import Credentials
    return AuthorizedSession(Credentials.from_service_account_file(
        SA, scopes=["https://www.googleapis.com/auth/drive.readonly"]))


def _r2():
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto")


def ensure_public_url(card: dict, sess=None, client=None) -> str:
    """投稿用の公開URLを用意する。一度上げた画像は URL をカードに控えて使い回す。

    投稿側（X/IG）が http URL を前提にしているため、実際に投稿する段では要る。

    2026-09-04: 下の「403で使えない」は誤診だった（実体は UA によるボット遮断）。
    ブラウザからは 200 で取得できる。以下は当時の記録として残す。
    ⚠ 2026-08-17 時点で R2 の公開URL（r2.dev）は 403 を返す。今回上げた画像も、
      以前から置かれている画像も同様なので、バケット側の公開設定の問題と思われる。
      そのため週次ループはこれを呼ばず、プレビューには preview_url() を使う。
      投稿を始める前に公開設定を直す必要がある。
    """
    if card.get("r2_url"):
        return card["r2_url"]
    if not os.getenv("R2_PUBLIC_URL"):
        return ""

    sess = sess or _drive_session()
    meta = sess.get(f"https://www.googleapis.com/drive/v3/files/{card['drive_id']}",
                    params={"fields": "thumbnailLink,mimeType"}).json()
    link = meta.get("thumbnailLink")
    if link:
        link = re.sub(r"=s\d+$", "=s1600", link)
        r = sess.get(link)
    else:
        r = sess.get(f"https://www.googleapis.com/drive/v3/files/{card['drive_id']}",
                     params={"alt": "media"})
    if r.status_code != 200 or len(r.content) < 1000:
        return ""

    ext = ".png" if "png" in (meta.get("mimeType") or "") else ".jpg"
    key = f"weekly/{card['id']}{ext}"
    client = client or _r2()
    client.upload_fileobj(
        io.BytesIO(r.content), os.getenv("R2_BUCKET_NAME"), key,
        ExtraArgs={"ContentType": "image/png" if ext == ".png" else "image/jpeg"})

    url = os.getenv("R2_PUBLIC_URL").rstrip("/") + "/" + key
    save_field(card, "r2_url", url)
    return url


def recent_kinds(limit: int = 3) -> list:
    """直近に使った場面種別を新しい順に返す。同じ種別が続くのを避けるために使う。

    最終使用日が記録されているカードを新しい順に並べる。厳密な投稿順ではないが、
    「最近この種別ばかり出している」を判定するには十分。
    """
    used = []
    for c in load_cards():
        if c.get("最終使用日"):
            try:
                used.append((date.fromisoformat(c["最終使用日"]), c["場面種別"] or ""))
            except ValueError:
                pass
    used.sort(key=lambda x: -x[0].toordinal())
    out = []
    for _, kind in used:
        if kind and kind not in out:
            out.append(kind)
        if len(out) >= limit:
            break
    return out


def record_use(card: dict, when: date = None) -> None:
    """使用実績を書き戻す。次回以降この画像は選ばれにくくなる。"""
    when = when or date.today()
    save_field(card, "使用回数", str(card.get("使用回数", 0) + 1))
    save_field(card, "最終使用日", when.isoformat())


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="記事の本文（または要旨）")
    ap.add_argument("--media", default="Instagram", choices=list(COUNT))
    ap.add_argument("--dry-run", action="store_true", help="R2へのアップロードをしない")
    args = ap.parse_args()

    cards = load_cards()
    print(f"候補カード: {len(cards)}枚（使用可否=可 のみ）")
    picked = pick(args.text, args.media, cards)
    for i, c in enumerate(picked, 1):
        print(f"\n{i}. {c['id']}  score={c['score']}")
        print(f"   {c['filename']}")
        print(f"   内容: {c['内容'][:70]}")
        print(f"   理由: {c['why']}")
        if not args.dry_run:
            print(f"   URL : {ensure_public_url(c) or '(取得できず)'}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    main()
