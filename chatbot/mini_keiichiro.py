#!/usr/bin/env python3
"""ミニ圭一郎 — サウンドヒーリング協会について答えるチャットボット（練習用）

使い方:
    python chatbot/mini_keiichiro.py            # 会話を始める
    python chatbot/mini_keiichiro.py --dry-run  # API を呼ばずに、渡す資料の量だけ確認する

終了するには「exit」と入力するか Ctrl+C。
APIキーは環境変数 ANTHROPIC_API_KEY（または .env）から読みます。
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONA = Path(__file__).resolve().parent / "persona.md"
KNOWLEDGE = ROOT / "knowledge"

MODEL = "claude-opus-5-5"


def read_field(text, name):
    """カード先頭（YAML風）の `name: 値` を1つ読む。なければ空文字。"""
    m = re.search(rf"^{name}:\s*(.*)$", text, re.MULTILINE)
    return m.group(1).split("#")[0].strip() if m else ""


def load_cards(folder, *, need_usable=False):
    """カードを読み込む。使用禁止（disputed）・使用不可のものは除く。"""
    cards = []
    for path in sorted(folder.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8")
        if read_field(text, "status") == "disputed":
            continue
        if need_usable and read_field(text, "usable") != "可":
            continue
        cards.append(text.strip())
    return cards


def org_basics():
    """CLAUDE.md の「団体情報」の節だけを取り出す。"""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    m = re.search(r"^## 団体情報\n(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def build_reference():
    """チャットボットに渡す参考資料を1つの文章にまとめる。"""
    sections = [
        ("団体の基本情報", [org_basics()]),
        ("協会誌まとめ（2011〜2025年）", [(ROOT / "資料まとめ.md").read_text(encoding="utf-8")]),
        ("圭一郎さんの言葉", load_cards(KNOWLEDGE / "voice", need_usable=True)),
        ("研究データ（原文と条件）", load_cards(KNOWLEDGE / "evidence")),
        ("体験談", load_cards(KNOWLEDGE / "testimonial", need_usable=True)),
        ("用語のやさしい説明", [(KNOWLEDGE / "glossary.md").read_text(encoding="utf-8")]),
        ("表現のルール", load_cards(KNOWLEDGE / "editorial")),
    ]
    parts = ["# 参考資料"]
    for title, items in sections:
        parts.append(f'<section title="{title}">\n' + "\n\n---\n\n".join(items) + "\n</section>")
    return "\n\n".join(parts)


def build_system():
    persona = PERSONA.read_text(encoding="utf-8")
    # 設定と資料は毎回同じなので、キャッシュして2回目以降の料金を下げる
    return [
        {"type": "text", "text": persona},
        {"type": "text", "text": build_reference(), "cache_control": {"type": "ephemeral", "ttl": "1h"}},
    ]


def ask(client, system, messages):
    """1回分の質問を送り、答えを流しながら表示する。返り値は最終メッセージ。"""
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=messages,
        output_config={"effort": "low"},  # 会話は low で十分。答えが浅ければ medium に
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # 安全上の理由で断られたとき、別のモデルで自動的にやり直す
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        print()
        return stream.get_final_message()


def main():
    parser = argparse.ArgumentParser(description="ミニ圭一郎チャットボット")
    parser.add_argument("--dry-run", action="store_true", help="API を呼ばずに資料の量だけ表示する")
    args = parser.parse_args()

    system = build_system()
    chars = sum(len(block["text"]) for block in system)
    print(f"渡す資料: 約{chars:,}文字")
    if args.dry_run:
        return

    import anthropic
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    client = anthropic.Anthropic()
    messages = []

    print("ミニ圭一郎と話せます。終わるときは exit と入力してください。\n")
    while True:
        try:
            question = input("あなた > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit", "終了"}:
            break
        if not question:
            continue

        messages.append({"role": "user", "content": question})
        print("ミニ圭一郎 > ", end="", flush=True)
        try:
            reply = ask(client, system, messages)
        except anthropic.AuthenticationError:
            sys.exit("APIキーが正しくありません。ANTHROPIC_API_KEY を確認してください。")
        except anthropic.APIError as e:
            print(f"\n（エラーが起きました: {e}）")
            messages.pop()
            continue

        if reply.stop_reason == "refusal":
            print("（この質問にはお答えできませんでした。言い方を変えてお試しください）")
            messages.pop()
            continue

        # 会話の続きのために、答えを丸ごと履歴に残す
        messages.append({"role": "assistant", "content": reply.content})
        u = reply.usage
        print(f"  [入力 {u.input_tokens} / キャッシュ読込 {u.cache_read_input_tokens} / 出力 {u.output_tokens} トークン]\n")


if __name__ == "__main__":
    main()
