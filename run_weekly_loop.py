#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""週次記事生成ループ（投稿はしない）。

  ①収集 → ②企画・執筆 → ③検証 → ④レビューシートへ投入
  投稿は行わない。人間が承認して初めて投稿キューへ移る。

投稿されないことの保証（二重）:
  1. 書き込み先は `週次_レビュー` タブ。投稿を行う x_auto_poster.py が読むのは `X投稿キュー` タブのみ
  2. 書き込むステータスは `AI下書き`。x_auto_poster.py が投稿するのは `投稿予約` のみ
  このスクリプトは X/Instagram の API を一切呼ばない（import すらしない）。

実行:
    /usr/bin/python3 run_weekly_loop.py                 # 通常（承認済みカードのみ使用）
    /usr/bin/python3 run_weekly_loop.py --test-cards    # 未承認カードも使う（ループ検証用）
    /usr/bin/python3 run_weekly_loop.py --no-write      # シートに書かず結果だけ表示
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import gspread

ROOT = Path(__file__).resolve().parent
EVID = ROOT / "knowledge" / "evidence"
RULES = ROOT / "knowledge" / "editorial"
LOGDIR = ROOT / "logs"

SPREADSHEET_KEY = "1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM"
TAB_REVIEW = "週次_レビュー"
TAB_BREAKDOWN = "週次_内訳"
EVENT_MASTER_TAB = "イベント予定"          # 予定の正本
EVENT_TABS = [EVENT_MASTER_TAB, "Xイベント投稿", "IGイベント投稿"]

# このスクリプトが書き込んでよい唯一のステータス。投稿トリガーの値とは別物
STATUS_DRAFT = "AI下書き"
STATUS_NEEDS_CHECK = "要確認あり"

# 媒体ごとの文字数の目安（CLAUDE.md の投稿ルールに準拠）
LIMITS = {"X": (0, 140), "Instagram": (300, 500), "note": (1500, 2500)}

# 恒久的に禁止する表現（圭一郎さん 2026-03-11 の指示より）
NG_PATTERNS = [
    (r"効果があります|効果が確認され|効果が実証", "X1 効果の断言"),
    (r"治る|治療|完治", "X3 医療行為との混同"),
    (r"ですら|すら反応", "X2 過度な強調"),
    (r"必ず|誰でも|100%", "X2 過度な強調"),
]

NUM = re.compile(r"\d+(?:[.,]\d+)*")

logger = logging.getLogger("weekly_loop")


# --------------------------------------------------------------------------
# ① 収集
# --------------------------------------------------------------------------

def norm(s: str) -> str:
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))
    return re.sub(r"(?<![\d.])\.(\d)", r"0.\1", s)


def load_cards(allow_draft: bool) -> list:
    """カードを読み込む。既定では status: active のものだけ。"""
    cards = []
    for p in sorted(EVID.glob("EV-*.md")):
        text = p.read_text(encoding="utf-8")

        def field(k):
            m = re.search(rf"^{k}:\s*(.*)$", text, re.M)
            return re.sub(r"\s+#.*$", "", m.group(1).strip()) if m else ""

        def blk(k):
            m = re.search(rf"^{k}:\s*\|\s*$(.*?)^\w[\w_]*:", text, re.S | re.M)
            return "\n".join(l.strip() for l in m.group(1).splitlines() if l.strip()) if m else ""

        status = field("status")
        if status == "disputed":
            continue
        if status != "active" and not allow_draft:
            continue

        # findings を構造のまま持つ。有意差なしの項目を落とさないため
        findings = []
        fb = re.search(r"^findings:\s*$(.*?)^\w[\w_]*:", text, re.S | re.M)
        if fb:
            for item in re.split(r"^\s*-\s+metric:", fb.group(1), flags=re.M)[1:]:
                def sub(k):
                    m = re.search(rf"^\s*{k}:\s*(.+)$", item, re.M)
                    return m.group(1).strip().strip('"') if m else ""
                findings.append({
                    "metric": item.splitlines()[0].strip(),
                    "result": sub("result"),
                    "value": sub("value") if sub("value") != "null" else "",
                    "significant": sub("significant").split("#")[0].strip(),
                })

        cards.append({
            "id": field("id"),
            "title": field("title"),
            "subjects": field("subjects"),
            "n": field("n"),
            "intervention": field("intervention"),
            "published": field("published"),
            "venue": field("venue"),
            "verbatim": blk("verbatim"),
            "limitations": blk("limitations"),
            "ng": blk("generalization_ng"),
            "findings": findings,
            "status": status,
        })
    return cards


def allowed_numbers(card: dict) -> set:
    """そのカードから引用してよい数値の集合。

    部分一致ではなく「数値トークンの集合」で持つ。空白を除去して部分一致を取ると
    隣接トークンが連結し（`Stim.1` + `80.9` → `Stim.180.9`）、境界判定が壊れるため。
    """
    src = " ".join([
        card["verbatim"], card["intervention"], card["subjects"], card["n"] or "",
        card["published"], card["venue"], card["title"],
        " ".join(f['{}'.format("value")] for f in card["findings"]),
    ])
    return set(NUM.findall(unicodedata.normalize("NFKC", src)))


# NG表現が否定形で使われている場合は違反ではない
# 例:「『効果が実証された』と書けるような話ではないのです」
NEGATION = re.compile(
    r"(ではあり?ません|ではない|ではなく|とは言えま?せん|とは言えない|"
    r"書けない|書けるような話ではない|できません|できない|限りま?せん|わけではない)"
)


def load_rules() -> list:
    if not RULES.is_dir():
        return []
    out = []
    for p in sorted(RULES.glob("RULE-*.md")):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^rule:\s*(.+)$", t, re.M)
        if m:
            out.append(m.group(1).strip())
    return out


def load_glossary() -> str:
    """用語の平易な説明。専門用語をそのまま出さないために渡す。"""
    p = ROOT / "knowledge" / "glossary.md"
    if not p.exists():
        return ""
    out = []
    for blk in re.split(r"^## (GL-\d+ .+)$", p.read_text(encoding="utf-8"), flags=re.M)[1:]:
        if blk.startswith("GL-"):
            out.append(f"### {blk}")
        else:
            plain = re.search(r"\*\*plain\*\*:\s*(.+)", blk)
            ng = re.search(r"\*\*ng\*\*:\s*\n((?:\s*-.+\n)+)", blk)
            ok = re.search(r"\*\*可\*\*:\s*(.+)", blk)
            if plain:
                out.append(f"- かみ砕いた説明: {plain.group(1).strip()}")
            if ng:
                items = [l.strip(" -") for l in ng.group(1).splitlines() if l.strip()]
                out.append("- この言い方は禁止: " + " / ".join(items))
            if ok:
                out.append(f"- 使ってよい言い方: {ok.group(1).strip()}")
    return "\n".join(out)


def parse_event_date(raw: str, today: date):
    """開催日セルを日付にする。読めなければ None。

    `イベント予定` は 2026-09-19 形式、旧タブは 9/19(土) 形式。両方受ける。
    月日だけの表記は年が無いので、今年→来年の順に見て未来側を採る。
    """
    m = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})/(\d{1,2})", raw)
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    for year in (today.year, today.year + 1):
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        if d >= today:
            return d
    return None


def load_events(gc, within_days: int = 21) -> list:
    """直近の予定を拾う。日付が読めないものは捨てる。

    正本は `イベント予定` タブ。旧タブも読むが、同じイベント名は正本を優先する。
    """
    today = date.today()
    horizon = today + timedelta(days=within_days)
    found = []
    sh = gc.open_by_key(SPREADSHEET_KEY)
    for tab in EVENT_TABS:
        try:
            rows = sh.worksheet(tab).get_all_values()
        except gspread.WorksheetNotFound:
            continue
        if not rows:
            continue
        hdr = rows[0]
        try:
            i_name = hdr.index("イベント名")
            i_date = hdr.index("開催日")
        except ValueError:
            continue
        def col(label):
            return hdr.index(label) if label in hdr else None

        i_place, i_time = col("開催場所"), col("時間")
        i_fee, i_apply = col("費用"), col("申込・問合せ")
        i_memo, i_src = col("詳細メモ"), col("情報源")

        for r in rows[1:]:
            if len(r) <= max(i_name, i_date):
                continue
            name, raw = r[i_name].strip(), r[i_date].strip()
            if not name or not raw:
                continue
            d = parse_event_date(raw, today)
            if not d or not (today <= d <= horizon):
                continue

            def cell(i):
                return r[i].strip() if i is not None and len(r) > i else ""

            found.append({
                "name": name, "date": d.isoformat(), "raw": raw,
                "place": cell(i_place), "time": cell(i_time), "fee": cell(i_fee),
                "apply": cell(i_apply), "memo": cell(i_memo), "source": cell(i_src),
                "canonical": tab == EVENT_MASTER_TAB,
            })

    # 同じイベント名は1件に絞る。正本タブの行を優先し、次に日付が近いものを採る。
    best = {}
    for e in sorted(found, key=lambda x: (not x["canonical"], x["date"])):
        best.setdefault(e["name"], e)
    return sorted(best.values(), key=lambda x: x["date"])


def load_recent(gc, limit: int = 24) -> list:
    """直近に生成した記事の「媒体・切り口・使用カード」を取り出す。

    同じカードと同じ季節ヒントから毎回生成するため、渡さないと切り口が収束する
    （2026-07-29〜31 の4回で X の導入が「寝苦しい夜」系に3回重複した）。
    """
    try:
        rows = gc.open_by_key(SPREADSHEET_KEY).worksheet(TAB_REVIEW).get_all_values()
    except Exception:
        return []
    out = []
    for r in rows[1:][-limit:]:
        if len(r) < 7 or not r[0].strip():
            continue
        body = r[6].replace("【ループ検証テスト・投稿しないでください】", "").strip()
        out.append({
            "媒体": r[2],
            "使用カード": r[5],
            "書き出し": body.split("\n")[0][:46] if body else "",
        })
    return out


def season_hint(d: date) -> str:
    m = d.month
    return {
        (12, 1, 2): "冬。空気が乾き、寝つきや冷えが気になる時期",
        (3, 4, 5): "春。環境の変化で気持ちが揺れやすい時期",
        (6, 7, 8): "夏。暑さと寝苦しさ、冷房による自律神経の乱れが気になる時期",
        (9, 10, 11): "秋。日照が減り、気分が沈みやすい時期",
    }[next(k for k in [(12, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11)] if m in k)]


def notify_severe(gc, alert: dict) -> None:
    """Lv2（重大災害）を検知したら、投稿を止めるか判断を仰ぐメールを送る。

    Lv1（大雨警報など）では送らない。年に数回しか鳴らない前提で、
    鳴ったときに必ず読まれる状態を保つ。
    """
    # 予約済みの件数を数える。判断材料としてメールに載せる
    pending = 0
    try:
        sh = gc.open_by_key(SPREADSHEET_KEY)
        for tab in ("X投稿キュー", "IG投稿キュー"):
            try:
                rows = sh.worksheet(tab).get_all_values()
            except Exception:
                continue
            if not rows or "ステータス" not in rows[0]:
                continue
            i = rows[0].index("ステータス")
            pending += sum(1 for r in rows[1:] if len(r) > i and r[i].strip() == "投稿予約")
    except Exception as e:
        logger.warning(f"予約件数の集計に失敗: {e}")

    logger.warning("=" * 60)
    logger.warning(f"⚠ 重大災害を検知しました: {alert.get('種別', '')}")
    logger.warning(f"   {alert.get('概要', '')}")
    logger.warning(f"   投稿予約になっている記事: {pending}件")
    logger.warning("=" * 60)

    body = "\n".join([
        "SNS記事生成ループが重大な災害を検知しました。",
        "",
        f"検知日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"種別    : {alert.get('種別', '（不明）')}",
        f"概要    : {alert.get('概要', '')}",
        f"検知語  : {', '.join(alert.get('検知語', [])) or '（LLM判定のみ）'}",
        "",
        f"■ 現在「投稿予約」になっている記事: {pending}件",
        "",
        "これらは15分毎の自動投稿で予定どおり投稿されます。",
        "平常運転で投稿してよいか、ご判断ください。",
        "",
        "止める場合はスプレッドシートの『X投稿キュー』『IG投稿キュー』で",
        "ステータスを「投稿予約」以外に変更してください。",
        "",
        "※ 今回の記事生成では時事ネタを使わず、常緑記事のみを作成しています。",
        "※ この通知は重大災害時のみ送られます（大雨警報などでは送りません）。",
    ])
    try:
        import os
        from notifier import GmailChannel, Notifier
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        except ImportError:
            pass

        # 宛先は既存の NOTIFY_GMAIL_TO（自動投稿の通知先＝圭一郎さん）とは分ける。
        # このループはまだ圭一郎さんに共有していないため、運用担当にだけ届ける。
        to = os.getenv("LOOP_NOTIFY_TO", "").strip()
        user = os.getenv("NOTIFY_GMAIL_USER", "").strip()
        pw = os.getenv("NOTIFY_GMAIL_APP_PASSWORD", "").strip()
        if not (to and user and pw):
            raise RuntimeError(
                "LOOP_NOTIFY_TO / NOTIFY_GMAIL_USER / NOTIFY_GMAIL_APP_PASSWORD が未設定です"
            )

        channel = GmailChannel(
            sender=user, app_password=pw,
            recipients=[r.strip() for r in to.split(",") if r.strip()],
            display_name="SNS週次ループ",
        )
        Notifier([channel])._broadcast(f"⚠ 重大災害を検知（投稿予約 {pending}件）", body)
        logger.warning(f"   → 通知メールを送信しました（宛先: {to}）")
    except Exception as e:
        logger.error(f"   → 通知メールの送信に失敗しました: {e}")
        logger.error("      ログを確認して手動で判断してください")


# --------------------------------------------------------------------------
# ② 企画・執筆
# --------------------------------------------------------------------------

def build_prompt(cards: list, events: list, rules: list, glossary: str,
                 contexts: list, recent: list, n_topics: int, today: date) -> str:
    # 原文全文は渡さない（プロンプトが肥大し生成が遅くなるため）。
    # 執筆に要るのは「何が分かったか」と「何を言ってはいけないか」。
    # 原文は検証工程で使う。
    def card_block(c: dict) -> str:
        fx = "\n".join(
            f"  - {f['metric']}: {f['result']}"
            + (f"（{f['value']}）" if f["value"] else "")
            + ("  ※有意差なし。効果として書かないこと" if f["significant"] == "false" else "")
            for f in c["findings"]
        ) or "  （数値データなし）"
        return f"""### {c['id']} {c['title']}
- 対象: {c['subjects']}（n={c['n'] or '不明'}）
- 介入: {c['intervention']}
- 分かったこと:
{fx}
- 限界: {c['limitations'] or '（記載なし）'}
- この結果から言ってはいけないこと:
{c['ng']}"""

    card_txt = "\n\n".join(card_block(c) for c in cards)

    if recent:
        used = {}
        for r in recent:
            for cid in (r.get("使用カード") or "").split(","):
                cid = cid.strip()
                if cid:
                    used[cid] = used.get(cid, 0) + 1
        lines = [f"- [{r['媒体']}] {r['書き出し']}" for r in recent[-12:]]
        if used:
            hot = ", ".join(f"{k}({v}回)" for k, v in sorted(used.items(), key=lambda x: -x[1])[:5])
            lines.append(f"\n直近で多く使われたカード: {hot} ← これ以外を優先してください")
        recent_txt = "\n".join(lines)
    else:
        recent_txt = "（まだありません。自由に選んでください）"
    # イベントは告知記事の材料になるので、書ける事実は全部渡す。
    # ただし空欄は空欄のまま渡す。埋まっていない項目を推測で補わせないため。
    ev_lines = []
    for e in events:
        ev_lines.append(f"- {e['date']} **{e['name']}**")
        for label, key in [("場所", "place"), ("時間", "time"),
                           ("費用", "fee"), ("申込・問合せ", "apply"), ("補足", "memo")]:
            if e.get(key):
                ev_lines.append(f"    - {label}: {e[key]}")
    ev_txt = "\n".join(ev_lines) or "（直近3週間に予定なし）"

    if contexts:
        ctx_txt = "\n".join(
            f"- {c.get('体感', '')}（{c.get('種類', '')}／〜{c.get('使える期限', '?')}）"
            for c in contexts
        )
        ctx_block = f"""
# いま多くの人が感じていること（記事の入り口に使ってよい）

{ctx_txt}

**使い方の制限:**
- これは**入り口の一文**にだけ使います。記事の主張は必ず根拠カードから作ってください
- 出来事を論評しない。「そうそう」と共感してもらうための一言に留める
- ここに書かれていない出来事を持ち出さない
- **この文脈を使った記事には、イベント告知・体験会案内・申込導線を入れないでください**
  （共感の入り口と集客を同じ記事に混ぜると、便乗している印象になります）
- 使った場合は `使った時事文脈` にその体感を書いてください
"""
    else:
        ctx_block = """
# いま多くの人が感じていること

（今回は使える文脈がありません。季節の一般的な描写に留めてください）
"""

    rule_txt = "\n".join(f"- {r}" for r in rules) or "（追加ルールなし）"

    return f"""あなたはサウンドヒーリング協会・ジョイファンデーションのSNS投稿を書く担当です。
今日は {today.isoformat()}。{season_hint(today)}。

# 使ってよい根拠（これ以外の事実・数値を書いてはいけない）

{card_txt}

# 直近のイベント

{ev_txt}
{ctx_block}
# 直近に出した記事（重複を避けてください）

{recent_txt}

**同じ書き出し・同じ切り口を繰り返さないでください。** 特に:
- 上と同じ導入（「寝苦しい夜」「暑い季節」など）を使い回さない
- 上で多く使われているカードは、今回は別のカードを優先する
- 同じ研究を紹介する場合でも、切り口（誰に向けて／どの場面で／何を問うか）を変える

同じことを繰り返し言うより、**まだ書いていない角度**を探してください。

# 専門用語の説明（本文に自然に織り込むこと。勝手な説明を作らない）

{glossary}

# 表現ルール（違反禁止）

- 「効果があります」「効果が確認されています」等の断言は禁止。「〜という報告があります」に留める
- 「治る」「改善する」「治療」は禁止（医療行為との混同）
- 「必ず」「誰でも」など過度な強調は禁止
- ハッシュタグは #KITAサウンドヒーリング を含める
{rule_txt}

# 厳守事項

1. **上の根拠に書かれていない数値を書いてはいけない。** 書きたい場合は本文中に `[要確認: 内容]` と残す
2. **「この結果から言ってはいけないこと」に該当する記述をしてはいけない**
3. 「自然音の聴取」と「体感音響（振動刺激）」は別物。混同しない
4. 押し売り感を出さない。安心して参加できそうなトーンにする

# 研究の限界の書き方（重要）

限界は事実として書きますが、**独立した見出しを立てて強調してはいけません**。
1セクション割くと「変化がなかったこと」が記事の主役になり、読者には
「それって意味あるの」という印象になります。**変化がないことは長所ではありません。**

- ❌ `## 同時に、変わらなかったものもあります` という見出しを立てて数段落書く
- ⭕ 数値を紹介した直後に一文で添える:
  「〜という報告があります。ただし参加者は7名と少なく、自律神経のバランスを示す指標には変化がありませんでした。」

限界に触れたあとは肯定的な内容に戻して締めてください。限界で記事を終わらせないこと。

# 専門用語の扱い（重要）

「コルチゾールが下がった」だけでは一般の読者に意味が伝わりません。
専門用語を出すときは、上の用語集の説明を**本文の流れの中に自然に**入れてください。

- ❌ 「コルチゾールが10.3→7.9μg/dLに減少しました」（説明なし）
- ❌ 「ストレスホルモンが減るのでリラックスできます」（効果の断言に飛躍）
- ⭕ 「ストレスを受けると増えるとされるホルモン（コルチゾール）が、聴取の前後で低い値になったという報告があります」

用語集の「この言い方は禁止」を必ず守ってください。

# 外部情報の申告（重要）

根拠カードに書かれていない記述は、**2種類に分けて**申告してください。
この振り分けで、人が精読すべき記事を絞り込みます。誤って振り分けないでください。

**`外部情報_季節生活`** — 事実確認が不要なもの:
- 「暑くて寝つけない季節です」など季節・天候の一般的な描写
- 「寝る前の10分」「音量は控えめに」など暮らしの提案
- 読者への語りかけ、書き手の姿勢表明

**`外部情報_要確認`** — 人の確認が要るもの:
- 「〜の機会をご用意しています」「体験会を行っています」などサービス・イベントの案内
- 「くわしくはプロフィールのリンクへ」など誘導文
- 団体の活動内容・実績・保有資料に関する記述
- 特定の日時・場所・料金

これらは数値でも禁止表現でもないため機械チェックでは検出できません。
**上のイベント一覧に載っていない催しを、あるかのように書かないでください。**

# 出力

{n_topics}本の投稿案を **JSONのみ** で出力してください。前後に説明文を付けないこと。

```json
[
  {{
    "媒体": "X | Instagram | note",
    "切り口": "一行でこの投稿の狙い",
    "本文": "投稿本文そのもの（ハッシュタグ含む）",
    "使用カードID": ["EV-0001"],
    "カード由来の文": "根拠カードに直接基づく部分だけを抜き出したもの",
    "AIの解釈": "あなたが補った解釈・つなぎの部分",
    "CTA": "行動喚起の文",
    "外部情報_季節生活": "季節・天候・暮らしの一般的な描写など、事実確認が不要なもの（なければ空文字）",
    "使った時事文脈": "上の「いま多くの人が感じていること」から使ったものがあれば、その体感をそのまま書く（使っていなければ空文字）",
    "外部情報_要確認": "**イベント・講座・サービスの案内、団体の活動や実績、プロフィールリンクへの誘導など、人の確認が要る主張**（なければ空文字）"
  }}
]
```

文字数は**厳守**してください（超えると差し戻しになります）:
- X: 140字以内（ハッシュタグ・改行を含めて数える。130字程度を目標に、余裕を持たせること）
- Instagram: 300〜500字（超えないこと）
- note: 1500〜2500字

媒体は偏らせず散らしてください。"""


def generate(prompt: str, timeout: int = 900) -> list:
    """claude CLI をヘッドレスで呼び、JSON配列を受け取る。

    生成結果は --no-write でも必ずファイルに残す。捨ててしまうと
    問題があったときに何が生成されたのか追えなくなる。
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (LOGDIR / f"prompt_{stamp}.txt").write_text(prompt, encoding="utf-8")
    logger.info(f"生成を開始します（claude -p / プロンプト {len(prompt):,}字）")

    started = datetime.now()
    try:
        out = run_llm(["claude", "-p", prompt, "--output-format", "text"], "執筆", timeout)
    except RuntimeError:
        (LOGDIR / f"generated_{stamp}.txt").write_text("(失敗)", encoding="utf-8")
        raise
    elapsed = (datetime.now() - started).total_seconds()
    (LOGDIR / f"generated_{stamp}.txt").write_text(out, encoding="utf-8")
    logger.info(f"生成に {elapsed:.0f}秒かかりました（logs/generated_{stamp}.txt に保存）")
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", out, re.S) or re.search(r"(\[.*\])", out, re.S)
    if not m:
        raise ValueError(f"JSONを取り出せませんでした:\n{out[:600]}")
    return json.loads(m.group(1))


# --------------------------------------------------------------------------
# ②-b 読み手視点レビュー（ChatGPT / Codex）と ②-c 改稿
#
# 執筆と同じモデルに自己採点させても甘くなる。別系統のモデル（OpenAI）に
# 読み手視点で見てもらい、その指摘を反映して書き直す。
# レビュアーには事実を足す権限を与えない（根拠カードの外に出ないため）。
# --------------------------------------------------------------------------

def run_llm(cmd: list, label: str, timeout: int, wall_limit: int = None) -> str:
    """LLM CLI を呼び、実時間（wall clock）でも打ち切る。

    subprocess の timeout は time.monotonic() で計られ、macOS ではスリープ中に
    進まない。launchd で無人実行するとスリープを跨ぐことがあり、実時間で数時間
    経過してしまう（2026-07-31 に実際に 9,168秒かかって失敗した）。
    そのため実時間でも上限を設ける。
    """
    wall_limit = wall_limit or timeout * 2
    started = datetime.now()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{label}: {timeout}秒でタイムアウトしました")

    elapsed = (datetime.now() - started).total_seconds()
    if elapsed > wall_limit:
        logger.warning(
            f"{label}: 実時間で {elapsed:.0f}秒かかりました"
            f"（上限 {wall_limit}秒）。スリープを跨いだ可能性があります"
        )
    if proc.returncode != 0:
        raise RuntimeError(f"{label}: 実行に失敗しました（{elapsed:.0f}秒）: {proc.stderr[:300]}")

    out = proc.stdout.strip()
    # claude -p は失敗時にも returncode 0 で短いメッセージだけ返すことがある
    if len(out) < 80 or out in ("Request timed out", "Execution error"):
        raise RuntimeError(f"{label}: 応答が不正です（{elapsed:.0f}秒）: {out[:120]!r}")
    return out


def _extract_json(text: str, what: str):
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.S) or re.search(r"(\[.*\])", text, re.S)
    if not m:
        raise ValueError(f"{what}: JSONを取り出せませんでした:\n{text[:600]}")
    return json.loads(m.group(1))


def review_with_codex(posts: list, timeout: int = 900) -> list:
    """ChatGPT（Codex CLI 経由）に読み手視点のレビューを依頼する。"""
    body = "\n\n".join(
        f"--- 記事{i + 1}（{p.get('媒体', '?')}／{len(p.get('本文', ''))}字）---\n{p.get('本文', '')}"
        for i, p in enumerate(posts)
    )
    prompt = f"""あなたはサウンドヒーリング協会のSNS投稿を、**一般読者の視点で**レビューします。
書き手ではなくレビュアーです。事実確認は別の工程で行うので、あなたは読み味だけ見てください。

{body}

# 見てほしい観点

1. **専門用語が分かりやすく説明されているか**
   「コルチゾールが下がった」だけでは一般の人に意味が伝わりません。
   何をする物質で、その変化がどういう文脈の話なのかが自然に書かれているか。
2. **研究の限界の書き方のバランス**
   限界を書くこと自体は必要ですが、独立した見出しを立てて強調すると
   「変化がなかったこと」が記事の主役になり、読者に「それって意味あるの」という
   印象を与えます。分量と位置が適切か。
3. **読みやすさ・流れ**  一般読者が最後まで読めるか。専門的すぎて離脱しないか。
4. **行動につながるか**  読み終えたあと何をすればいいか分かるか。押し売り感がないか。

# 絶対に守ること

- **新しい事実・数値・研究結果を提案してはいけません。** 根拠が限定されています
- 「この数値を足すといい」「別の研究も引用すると良い」といった提案は禁止
- 効果を断言する方向の提案は禁止（薬機法・景品表示法のリスクがあります）
- あなたの仕事は「今ある材料の伝え方」の改善提案です

# 出力

**JSONのみ**を出力してください。説明文を前後に付けないこと。

```json
[
  {{
    "記事番号": 1,
    "総評": "一行で",
    "良い点": "そのまま残すべき点",
    "改善提案": ["具体的な直し方を箇条書きで。抽象論ではなく、どこをどう変えるか"]
  }}
]
```"""
    logger.info("②-b ChatGPT（Codex）に読み手視点レビューを依頼します")
    started = datetime.now()
    # 実行用コピー（~/joyfoundation-loop-runtime）は git リポジトリではないため
    # --skip-git-repo-check が要る。付けないと codex が起動を拒否する
    proc = subprocess.run(
        ["codex", "exec", "--skip-git-repo-check", prompt],
        capture_output=True, text=True, timeout=timeout, cwd=str(ROOT),
    )
    elapsed = (datetime.now() - started).total_seconds()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (LOGDIR / f"review_codex_{stamp}.txt").write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"codex の実行に失敗しました: {proc.stderr[:400]}")
    reviews = _extract_json(proc.stdout, "Codexレビュー")
    logger.info(f"②-b レビュー取得（{elapsed:.0f}秒 / {len(reviews)}件）")
    return reviews


def revise(posts: list, reviews: list, base_prompt: str, timeout: int = 900) -> list:
    """レビュー指摘を反映して書き直させる。制約は初稿と同じものを再提示する。"""
    pairs = []
    for i, p in enumerate(posts):
        rv = next((r for r in reviews if r.get("記事番号") == i + 1), {})
        sug = "\n".join(f"    - {s}" for s in rv.get("改善提案", [])) or "    - （指摘なし）"
        pairs.append(
            f"--- 記事{i + 1}（{p.get('媒体', '?')}）---\n"
            f"【現在の本文】\n{p.get('本文', '')}\n\n"
            f"【レビュアーの総評】{rv.get('総評', '')}\n"
            f"【残すべき良い点】{rv.get('良い点', '')}\n"
            f"【改善提案】\n{sug}"
        )

    prompt = f"""{base_prompt}

---

# ここからが今回の作業

上の制約はそのまま有効です。以下は初稿と、一般読者視点のレビュアーからの指摘です。
指摘を反映して**書き直して**ください。

{chr(10).join(pairs)}

# 書き直しの注意

- **レビュアーの指摘でも、上の制約に反するものは採用しないでください。**
  特に「根拠にない数値を足す」「効果を断言する」提案は無視すること
- 良い点として挙がった部分は壊さないこと
- 媒体・切り口・使用カードIDは変えないこと
- 出力形式は初稿と同じJSON配列（媒体／切り口／本文／使用カードID／カード由来の文／AIの解釈／CTA／外部情報）

**JSONのみ**を出力してください。"""

    logger.info("②-c 指摘を反映して改稿します")
    started = datetime.now()
    proc = subprocess.run(["claude", "-p", prompt, "--output-format", "text"],
                          capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    elapsed = (datetime.now() - started).total_seconds()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (LOGDIR / f"revised_{stamp}.txt").write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"改稿に失敗しました: {proc.stderr[:400]}")
    revised = _extract_json(proc.stdout, "改稿")
    logger.info(f"②-c 改稿完了（{elapsed:.0f}秒 / {len(revised)}本）")
    return revised


# --------------------------------------------------------------------------
# ③ 検証（執筆とは別工程。自己採点にしない）
# --------------------------------------------------------------------------

def verify(post: dict, cards: dict) -> dict:
    """機械チェック。問題を列挙し、分級を決める。"""
    body = post.get("本文", "")
    problems = []

    used = [i for i in post.get("使用カードID", []) if i]
    for cid in used:
        if cid not in cards:
            problems.append(f"存在しないカードIDを参照: {cid}")

    # 本文の数値が、参照カードの原文・結果に実在するか
    allowed = set()
    for c in used:
        if c in cards:
            allowed |= allowed_numbers(cards[c])
    # 時刻・料金はイベント予定タブ由来で、根拠カードとは無関係。数値を数える前に伏せる。
    # 「18:00〜19:00」は 18 と 19 だけが時刻として除外され、分の 00 が取り残されて
    # 誤検出になっていた（2026-08-17）。表記ごとまとめて伏せる方が確実。
    scan = unicodedata.normalize("NFKC", body)
    scan = re.sub(r"\d{1,2}\s*[:：]\s*\d{2}", "〈時刻〉", scan)
    # 料金は「3,300円」「3000円」どちらもありうる。単位付きの額（45.4兆円 等）は
    # 間に兆・億が挟まるのでここでは伏せず、通常どおり照合に回る。
    scan = re.sub(r"\d{1,3}(?:,\d{3})+\s*円|\d+\s*円", "〈金額〉", scan)

    for n in NUM.findall(scan):
        if len(n) <= 1:
            continue
        # 日付は根拠カードとは無関係（イベント告知等）なので除外する。
        # 年号は除外しない（出典年の取り違えを見逃さないため、カードの published/venue と照合する）
        if re.search(rf"{re.escape(n)}\s*(月|日|時|分)", body):
            continue
        if n not in allowed:
            problems.append(f"根拠にない数値: {n}")

    for pat, label in NG_PATTERNS:
        for m in re.finditer(pat, body):
            # 直後が否定形なら違反ではない（「〜とは言えません」等）
            if NEGATION.search(body[m.end():m.end() + 30]):
                continue
            problems.append(f"NG表現（{label}）: {m.group(0)}")
            break

    media = post.get("媒体", "")
    lo, hi = LIMITS.get(media, (0, 10**9))
    length = len(body)
    if length > hi or (lo and length < lo):
        problems.append(f"文字数が目安外: {length}字（目安 {lo}〜{hi}）")

    if not re.search(r"#KITAサウンドヒーリング", body) and media in ("X", "Instagram"):
        problems.append("ハッシュタグ #KITAサウンドヒーリング がない")

    # 分級: 外部情報や新規数値があるほど厳しく見る
    # 季節描写まで C にすると全記事が C になり分級の意味がなくなる。
    # 人の確認が要る外部情報（サービス・イベント・団体の主張）だけを C とする。
    if any(p.startswith("根拠にない数値") for p in problems) or post.get("外部情報_要確認", "").strip():
        grade = "C: 新規数値・ニュース・医療的表現を含む"
    elif post.get("AIの解釈", "").strip() or post.get("外部情報_季節生活", "").strip():
        grade = "B: 新しい組み合わせ・解釈を含む"
    else:
        grade = "A: 確認済みカードの言い換えのみ"

    # 時事文脈を使った記事に集客導線を混ぜない（便乗に見えるため機械で弾く）
    if post.get("使った時事文脈", "").strip():
        for pat in (r"体験会", r"お申[しこ]み", r"申込", r"プロフィールのリンク",
                    r"ご予約", r"参加者募集", r"受付中", r"ご用意しています"):
            if re.search(pat, body):
                problems.append(
                    f"時事文脈を使った記事に集客導線があります（「{re.search(pat, body).group(0)}」）"
                )
                break

    if "[要確認" in body:
        problems.append("本文に [要確認] タグが残っている")

    return {"problems": problems, "grade": grade}


# --------------------------------------------------------------------------
# ④ レビューシートへ投入
# --------------------------------------------------------------------------

def publish(gc, posts: list, results: list, reviews: list, test_mode: bool) -> int:
    sh = gc.open_by_key(SPREADSHEET_KEY)
    rw = sh.worksheet(TAB_REVIEW)
    bd = sh.worksheet(TAB_BREAKDOWN)

    existing = rw.get_all_values()
    start = len(existing) + 1 if len(existing) > 1 else 2
    seq = sum(1 for r in existing[1:] if r and r[0].strip())

    today = date.today()
    week = f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows, breakdown = [], []
    for i, (post, res) in enumerate(zip(posts, results)):
        aid = f"{'TEST-' if test_mode else ''}ART-{seq + i + 1:04d}"
        status = STATUS_NEEDS_CHECK if res["problems"] else STATUS_DRAFT
        body = post.get("本文", "")
        if test_mode:
            body = "【ループ検証テスト・投稿しないでください】\n\n" + body
        rows.append([
            aid, week, post.get("媒体", ""), "", res["grade"],
            ", ".join(post.get("使用カードID", [])),
            body, status, "", "", "", "", "", stamp,
        ])
        rv = next((r for r in reviews if r.get("記事番号") == i + 1), {})
        rv_txt = ""
        if rv:
            rv_txt = f"【総評】{rv.get('総評', '')}\n【改善提案】\n" + \
                     "\n".join(f"・{s}" for s in rv.get("改善提案", []))
        breakdown.append([
            aid, post.get("カード由来の文", ""), post.get("AIの解釈", ""),
            post.get("CTA", ""), post.get("使った時事文脈", ""),
            post.get("外部情報_季節生活", ""), post.get("外部情報_要確認", ""),
            "\n".join(res["problems"]), rv_txt,
        ])

    # ネットワークエラーで生成物を捨てないよう再試行する。
    # 2026-08-01 に Connection reset by peer で3本分（生成に15分）を失った。
    def write(ws, values, at):
        import time
        last = None
        for i in range(4):
            try:
                ws.update(values=values, range_name=at)
                return
            except Exception as e:
                last = e
                wait = 3 * (2 ** i)
                logger.warning(f"シート書き込みに失敗（{i+1}/4）: {type(e).__name__}。{wait}秒後に再試行")
                time.sleep(wait)
        raise last

    write(rw, rows, f"A{start}")
    bd_existing = bd.get_all_values()
    bd_start = len(bd_existing) + 1 if len(bd_existing) > 1 else 2
    write(bd, breakdown, f"A{bd_start}")
    return len(rows)


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-cards", action="store_true",
                    help="未承認カードも使う（ループ検証用。出力にテスト表示が付く）")
    ap.add_argument("--no-write", action="store_true", help="シートに書き込まない")
    ap.add_argument("--with-news", action="store_true",
                    help="時事文脈を収集して記事の入り口に使う（実験）")
    ap.add_argument("--news-file",
                    help="時事文脈をJSONファイルから読む（平常時を模した検証用）")
    ap.add_argument("--no-review", action="store_true",
                    help="ChatGPT(Codex)レビューと改稿を行わない")
    ap.add_argument("--topics", type=int, default=3, help="生成する本数（既定3）")
    args = ap.parse_args()

    LOGDIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOGDIR / "weekly_loop.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info("=" * 60)
    logger.info("週次ループ開始（投稿は行いません）")

    # 実行用コピーで動いている場合、知識層が古いままだと承認が反映されない
    synced = ROOT / ".synced_at"
    if synced.exists():
        from datetime import datetime as _dt
        try:
            age = (_dt.now() - _dt.fromisoformat(synced.read_text().strip())).days
            if age >= 3:
                logger.warning(
                    f"!! 知識層の同期が {age}日前です。カードを承認した場合は "
                    "プロジェクト側で ./sync_loop_runtime.sh を実行してください"
                )
        except ValueError:
            pass

    gc = gspread.service_account()

    # ① 収集
    cards = load_cards(allow_draft=args.test_cards)
    if not cards:
        logger.error("使用できるカードが0枚です。")
        logger.error("承認済み(status: active)のカードがありません。")
        logger.error("スプレッドシートの『週次_カード承認』で承認し、")
        logger.error("  /usr/bin/python3 sync_approvals.py --apply")
        logger.error("を実行してください。ループ検証だけしたい場合は --test-cards を付けてください。")
        return 1

    contexts = []
    if args.news_file:
        contexts = json.loads(Path(args.news_file).read_text(encoding="utf-8"))
        logger.warning(f"!! --news-file: 手動指定の時事文脈 {len(contexts)}件を使用（検証用）")
        for c in contexts:
            logger.info(f"     ・{c.get('体感', '')}")
    elif args.with_news:
        try:
            from collect_context import collect_with_alert
            contexts, alert = collect_with_alert(verbose=False)
            if alert:
                notify_severe(gc, alert)
            logger.info(f"①-b 時事文脈: {len(contexts)}件を採用")
            for c in contexts:
                logger.info(f"     ・{c.get('体感', '')}（〜{c.get('使える期限', '?')}）")
            if not contexts:
                logger.warning("     使える文脈が0件でした（キルスイッチ作動またはフィルタ全除外）")
        except Exception as e:
            logger.warning(f"時事文脈の収集に失敗しました: {e}")
            logger.warning("常緑記事のみ生成します。")

    events = load_events(gc)
    rules = load_rules()
    glossary = load_glossary()
    n_terms = glossary.count("### GL-")
    logger.info(
        f"① 収集: カード{len(cards)}枚 / イベント{len(events)}件 / "
        f"ルール{len(rules)}件 / 用語{n_terms}件"
    )
    if args.test_cards:
        logger.warning("!! --test-cards: 未承認カードを使用しています。生成物は本番利用不可です")

    # ② 企画・執筆
    recent = load_recent(gc)
    if recent:
        logger.info(f"①-c 直近の記事 {len(recent)}件を重複回避のため参照")
    prompt = build_prompt(cards, events, rules, glossary, contexts, recent,
                          args.topics, date.today())
    posts = generate(prompt)
    logger.info(f"② 執筆: {len(posts)}本を生成")

    # ②-b/②-c 別系統モデルによる読み手視点レビューと改稿
    reviews = []
    if not args.no_review:
        try:
            reviews = review_with_codex(posts)
            posts = revise(posts, reviews, prompt)
        except Exception as e:
            logger.warning(f"レビュー／改稿をスキップしました: {e}")
            logger.warning("初稿をそのまま使います。")
    else:
        logger.info("②-b/②-c: --no-review のためスキップ")

    # ③ 検証
    cmap = {c["id"]: c for c in cards}
    results = [verify(p, cmap) for p in posts]
    ng = sum(1 for r in results if r["problems"])
    logger.info(f"③ 検証: 問題あり {ng}本 / 問題なし {len(results) - ng}本")
    for p, r in zip(posts, results):
        head = f"{p.get('媒体', '?')} | {r['grade'].split(':')[0]} | {len(p.get('本文', ''))}字"
        if r["problems"]:
            logger.warning(f"  △ {head}")
            for x in r["problems"]:
                logger.warning(f"      - {x}")
        else:
            logger.info(f"  ○ {head}")

    # ④ 投入
    if args.no_write:
        logger.info("④ 投入: --no-write のため書き込みませんでした")
    else:
        try:
            n = publish(gc, posts, results, reviews, args.test_cards)
            logger.info(f"④ 投入: 週次_レビュー に {n}行を追加（ステータス: {STATUS_DRAFT}／{STATUS_NEEDS_CHECK}）")
        except Exception as e:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rescue = LOGDIR / f"unpublished_{stamp}.json"
            rescue.write_text(json.dumps(
                {"posts": posts, "results": results, "reviews": reviews,
                 "test_mode": args.test_cards}, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.error(f"④ 投入に失敗しました: {type(e).__name__}: {str(e)[:120]}")
            logger.error(f"   生成物は {rescue.name} に退避しました。")
            logger.error("   復旧: /usr/bin/python3 republish.py <ファイル>")
            return 1

    logger.info("完了。投稿は行っていません。")
    logger.info("投稿するには、人が内容を確認し『X投稿キュー』へ移した上で「投稿予約」にする必要があります。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
