#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""記事の「入り口」に使える時事文脈を収集する（実験）。

## 何を集めるか

ニュース事象ではなく、**多くの人が今同時に感じている体感**を集める。
狙いは論評ではなく、リアルタイムの共感と人間味。

  ⭕ 「雨が続いてジメジメする」「寝苦しい夜が続く」「夏フェスの季節」
  ❌ 「台風で〇〇に被害」「地震が発生」「〇〇氏が辞任」

## 二重の安全装置

1. **除外カテゴリ**: 取得段階でLLMに除外させる（一次フィルタ）
2. **禁止語の機械チェック**: LLMの自己申告を信用せず、キーワードで落とす（二次フィルタ）
   Codex 指摘「LLMは上手な便乗を作って通す」ため、機械ルールを最終防衛線にする
3. **キルスイッチ**: 警報級の気象・重大災害を検知したら時事枠を丸ごと停止する

実行:
    /usr/bin/python3 collect_context.py            # 収集して表示するだけ
    /usr/bin/python3 collect_context.py --json     # JSON で出力
"""

import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGDIR = ROOT / "logs"

# --- 二次フィルタ: これらの語を含む文脈は機械的に落とす ---------------------
# LLM の自己申告を信用しないための最終防衛線。迷ったら落とす側に倒す。
BLOCKED = {
    "災害": ["地震", "震度", "津波", "噴火", "土砂", "洪水", "浸水", "冠水", "氾濫",
             "避難", "被災", "被害", "全壊", "半壊", "停電", "断水"],
    "気象警報": ["警報", "特別警報", "暴風", "記録的", "危険度", "命を守る", "不要不急"],
    "人的被害": ["死亡", "死者", "負傷", "けが人", "行方不明", "搬送", "救助"],
    "事件事故": ["事件", "事故", "逮捕", "容疑", "殺人", "火災", "墜落", "衝突", "詐欺"],
    "政治": ["選挙", "首相", "内閣", "政権", "与党", "野党", "国会", "増税", "法案", "汚職"],
    "経済困窮": ["倒産", "解雇", "リストラ", "物価高", "値上げ", "破綻", "失業"],
    "健康危機": ["感染", "流行", "熱中症", "パンデミック", "ワクチン", "食中毒"],
    "人物": ["死去", "訃報", "逝去", "引退", "不倫", "謝罪", "炎上", "スキャンダル",
             "入院", "闘病", "書類送検"],
    "社会対立": ["差別", "ハラスメント", "抗議", "デモ", "訴訟", "提訴", "batalla"],
    "戦争": ["戦争", "侵攻", "テロ", "軍事", "空爆", "停戦"],
}

# --- Lv1: 時事枠を止める（頻繁に発動してよい。通知しない） ------------------
# 大雨警報・暴風警報は日本では頻繁に出る。時事ネタを使わないだけなので実害はない。
KILL_SWITCH = ["特別警報", "大雨警報", "暴風警報", "津波", "噴火", "震度5", "震度6", "震度7",
               "記録的な大雨", "命を守る行動"]

# 「〜の発表はなく」「〜もなし」のように、危険語が“無かったこと”の説明として
# 現れる場合がある。根拠テキストは平常時ほどこの形で危険語を並べるため、
# 素朴な部分一致だとキルスイッチが毎回誤作動する（2026-08-04〜17 に実際に発生）。
NO_EVENT = re.compile(
    r"(はなく|もなく|はなし|もなし|ありません|ございません|"
    r"されていない|されていません|出ていない|出ていません|"
    r"未発表|該当なし|発表なし|なし。|なし$|"
    r"警報級ゼロ|ゼロ|0件|いずれも注意報|注意報のみ)"
)

# 「気象特別警報・警報・注意報」は気象庁の**文書名**であって、
# 発表されたという意味ではない。2026-08-24 にこれを災害と誤読して
# 通知メールを送った。判定前にこうした定型句を伏せる。
DOC_NAMES = re.compile(
    r"気象特別警報・警報・注意報|特別警報・警報・注意報|"
    r"警報・注意報(?:一覧|情報|文書)?|噴火警戒レベル(?=は)"
)

# --- Lv2: 投稿停止の判断を人に仰ぐ（年に数回。メール通知する） ---------------
# 「協会として平常運転で投稿してよいか」という組織判断が要る規模に限定する。
# ここを緩くすると通知が読まれなくなり、本当に重大なときに見落とされる。
SEVERE = ["特別警報", "震度6", "震度7", "津波警報", "大津波",
          "噴火警戒レベル4", "噴火警戒レベル5", "死者", "行方不明"]

FETCH_PROMPT = """今日は {today} です。日本国内で、いま多くの人が**体で感じていること**を調べてください。

# 集めるもの

ニュース事象そのものではなく、**共有された体感・気分**です。
SNS投稿の「入り口の一文」に使い、読者に「そうそう」と思ってもらうためのものです。

- 天候の体感（暑い／ジメジメする／寝苦しい／涼しくなってきた など）
- 季節の区切り（二十四節気、月の変わり目、学校の長期休暇 など）
- 文化・行楽の季節感（夏フェス、花火、帰省、紅葉 など。開催済み・開催中のもの）

# 絶対に集めないもの（1つでも該当したら、その項目ごと捨てる）

- 災害、被害、避難、停電、断水に関するもの
- 気象警報・注意報が発令されている状況
- 死傷者、行方不明者、救助に関するもの
- 事件、事故、火災
- 政治、選挙、経済政策、物価、倒産、失業
- 感染症、熱中症搬送、公衆衛生上の警告
- 特定の個人（著名人含む）の病気・不祥事・訃報
- 差別、人権、宗教、対立、訴訟
- 戦争、テロ

**迷ったら捨ててください。** 取りこぼしは問題ありませんが、危険なものを通すことは重大な問題です。

# 追加で確認してほしいこと

1. いま日本のどこかで**気象警報が発令されているか**を確認し、`災害警戒中` に true/false で
   答えてください。該当する場合、この収集結果は使われません。

2. さらに、以下のいずれかに該当する**重大な災害**が起きているかを `重大災害` に答えてください。

   - 最大震度6弱以上の地震
   - 気象庁の**特別警報**（大雨・暴風・高潮・波浪・大雪）
   - 津波警報以上（注意報は除く）
   - 噴火警戒レベル4以上
   - 死者・行方不明者が出ている広域災害

   **該当しない場合は必ず false にしてください。** 大雨警報・暴風警報だけでは該当しません。

# 出力

**JSONのみ**を出力してください。前後に説明を付けないこと。

```json
{{
  "災害警戒中": false,
  "重大災害": {{ "該当": false, "種別": "", "概要": "" }},
  "根拠": "確認した内容を一行で",
  "文脈": [
    {{
      "体感": "多くの人が今感じていること。一文で",
      "種類": "天候の体感 | 季節の区切り | 文化・行楽",
      "使える期限": "YYYY-MM-DD（この日を過ぎたら古くなる）",
      "備考": "補足があれば"
    }}
  ]
}}
```

3〜6件程度で構いません。該当がなければ `文脈` は空配列にしてください。"""


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def screen(item: dict) -> str:
    """禁止語による二次フィルタ。落とす理由を返す（問題なければ空文字）。"""
    blob = norm(" ".join(str(v) for v in item.values()))
    for category, words in BLOCKED.items():
        for w in words:
            if w in blob:
                return f"{category}（「{w}」を含む）"
    return ""


def kill_hits(data: dict) -> list:
    """キルスイッチを発動させるべき検知語を返す（空なら平常）。

    文脈アイテムは本文なので素朴に走査する。一方 `根拠` は「災害が無いこと」を
    説明する文章であり、平常時ほど危険語が並ぶ。そのため句ごとに区切り、
    否定表現を伴う句は数えない。判定に迷う場合は発動側（安全側）に倒す。
    """
    hits = []

    # 文脈アイテム: 本文なのでそのまま見る
    body = norm(json.dumps(data.get("文脈", []), ensure_ascii=False))
    hits += [w for w in KILL_SWITCH if w in body]

    # 根拠: 句に割り、否定されていない句だけを見る
    reason = DOC_NAMES.sub("〈文書名〉", norm(data.get("根拠", "")))
    for clause in re.split(r"[、。\n]", reason):
        if NO_EVENT.search(clause):
            continue
        hits += [w for w in KILL_SWITCH if w in clause]

    # LLM が重大災害を申告している場合は、根拠文の言い回しに関わらず止める。
    # Lv2（通知）が鳴るのに Lv1（時事枠の停止）が鳴らない状態を作らないため。
    declared = data.get("重大災害", {}) or {}
    if declared.get("該当"):
        hits.append(declared.get("種別") or "重大災害の申告")

    return sorted(set(hits))


def fetch(today: date, timeout: int = 600, retries: int = 3) -> dict:
    prompt = FETCH_PROMPT.format(today=today.isoformat())
    LOGDIR.mkdir(exist_ok=True)
    last = ""

    for attempt in range(1, retries + 1):
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text"],
                capture_output=True, text=True, timeout=timeout, cwd=str(ROOT),
            )
        except subprocess.TimeoutExpired:
            # 応答が返らないのは通信不良が原因のことが多く、再試行で回復する。
            last = f"{timeout}秒でタイムアウトしました"
            if attempt < retries:
                wait = 15 * (2 ** (attempt - 1))
                print(f"  収集に失敗（{attempt}/{retries}）: {last}", file=sys.stderr)
                print(f"  {wait}秒待って再試行します。", file=sys.stderr)
                time.sleep(wait)
            continue

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        (LOGDIR / f"context_raw_{stamp}.txt").write_text(proc.stdout, encoding="utf-8")

        # claude CLI は API エラーを stdout に書く。stderr だけ見ると原因が空になる。
        detail = (proc.stderr.strip() or proc.stdout.strip())[:300] or "(出力なし)"

        if proc.returncode == 0:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", proc.stdout, re.S) \
                or re.search(r"(\{.*\})", proc.stdout, re.S)
            if m:
                return json.loads(m.group(1))
            last = f"JSONを取り出せませんでした: {detail}"
        else:
            last = f"claude が異常終了しました (rc={proc.returncode}): {detail}"

        if attempt < retries:
            wait = 15 * (2 ** (attempt - 1))   # 15s → 30s → (60s)
            print(f"  収集に失敗（{attempt}/{retries}）: {last}", file=sys.stderr)
            print(f"  {wait}秒待って再試行します。", file=sys.stderr)
            time.sleep(wait)

    raise RuntimeError(f"収集に失敗しました（{retries}回試行）: {last}")


def severe_hits(data: dict) -> list:
    """Lv2 の検知語のうち、否定されていないものを返す。

    kill_hits と同じ考え方。文脈アイテムは本文なので素朴に走査し、
    `根拠` は「災害が無いこと」の説明であることが多いので句ごとに見る。
    """
    hits = []
    body = norm(json.dumps(data.get("文脈", []), ensure_ascii=False))
    hits += [w for w in SEVERE if w in body]

    reason = DOC_NAMES.sub("〈文書名〉", norm(data.get("根拠", "")))
    for clause in re.split(r"[、。\n]", reason):
        if NO_EVENT.search(clause):
            continue
        hits += [w for w in SEVERE if w in clause]

    # 「重大災害」欄の概要は、該当と申告された場合だけ見る
    declared = data.get("重大災害", {}) or {}
    if declared.get("該当"):
        summary = norm(str(declared.get("概要", "")))
        hits += [w for w in SEVERE if w in summary]

    return sorted(set(hits))


def assess_severe(data: dict) -> dict:
    """Lv2（投稿停止の判断が要る規模）に該当するか判定する。

    LLMの自己申告と機械的な語句検知の両方を見る。
    どちらか一方でも該当すれば人に判断を仰ぐ（見落としより空振りを選ぶ）。
    """
    # 2026-08-24: ここが JSON 全体を素朴に走査しており、
    # 「特別警報・津波情報なし」という**災害が無いことの説明**を検知して
    # 誤って通知メールを送った。kill_hits と同じく否定表現を除外する。
    # 空振りは許すが、毎回空振りすると本当の災害時に無視されるようになる。
    hits = severe_hits(data)
    declared = data.get("重大災害", {}) or {}
    if not (declared.get("該当") or hits):
        return {}
    return {
        "種別": declared.get("種別", "") or "／".join(hits),
        "概要": declared.get("概要", "") or data.get("根拠", ""),
        "検知語": hits,
    }


def collect(today: date = None, verbose: bool = True) -> list:
    """時事文脈を収集し、安全なものだけ返す。危険時は空リストを返す。"""
    today = today or date.today()
    data = fetch(today)

    raw = data.get("文脈", [])
    if verbose:
        print(f"取得: {len(raw)}件 / 災害警戒中={data.get('災害警戒中')}")
        print(f"根拠: {data.get('根拠', '')}")

    # --- キルスイッチ -----------------------------------------------------
    hits = kill_hits(data)
    if data.get("災害警戒中") or hits:
        if verbose:
            reason = "災害警戒中の申告" if data.get("災害警戒中") else f"検知語 {hits}"
            print(f"\n⛔ キルスイッチ作動（{reason}）")
            print("   時事文脈は使用しません。常緑記事のみ生成してください。")
        return []

    # --- 二次フィルタ -----------------------------------------------------
    safe, dropped = [], []
    for item in raw:
        reason = screen(item)
        (dropped if reason else safe).append((item, reason))

    if verbose:
        for item, reason in dropped:
            print(f"  ✗ 除外[{reason}]: {item.get('体感', '')[:40]}")
        for item, _ in safe:
            exp = item.get("使える期限", "?")
            print(f"  ○ 採用（〜{exp}）: {item.get('体感', '')}")
        if dropped:
            print(f"\n二次フィルタで {len(dropped)}件 を除外しました。")

    # 期限切れを落とす
    alive = []
    for item, _ in safe:
        try:
            if date.fromisoformat(item.get("使える期限", "")) >= today:
                alive.append(item)
        except (ValueError, TypeError):
            alive.append(item)   # 期限が読めないものは残す（人が見る）
    return alive


def collect_with_alert(today: date = None, verbose: bool = True):
    """時事文脈と、Lv2アラート（あれば）を返す。

    戻り値: (使える文脈のリスト, Lv2アラート dict または None)
    """
    today = today or date.today()
    data = fetch(today)
    alert = assess_severe(data)

    hits = kill_hits(data)
    if data.get("災害警戒中") or hits:
        if verbose:
            reason = "災害警戒中の申告" if data.get("災害警戒中") else f"検知語 {hits}"
            print(f"⛔ キルスイッチ作動（{reason}）→ 時事文脈は使用しません")
        return [], (alert or None)

    safe = [i for i in data.get("文脈", []) if not screen(i)]
    alive = []
    for item in safe:
        try:
            if date.fromisoformat(item.get("使える期限", "")) >= today:
                alive.append(item)
        except (ValueError, TypeError):
            alive.append(item)
    return alive, (alert or None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="JSONで出力する")
    args = ap.parse_args()
    try:
        items = collect(verbose=not args.json)
    except Exception as e:
        print(f"収集に失敗しました: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print(f"\n最終的に使える文脈: {len(items)}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
