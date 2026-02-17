#!/usr/bin/env python3
"""
資料処理スクリプト - OpenAI API を使用して PDF/DOCX ファイルを構造化
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# PDF/DOCX テキスト抽出
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None

# .env から API キーを読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 処理用プロンプト
PROMPT_TEMPLATE = """
以下のドキュメント内容を読み込み、指定の形式で出力してください。

【ドキュメント名】: {filename}

【ドキュメント内容】:
{content}

---

【出力形式】:

## {filename}

**カテゴリ**: [学会発表/論文/体験談/解説/イベント報告/協会誌/その他から選択]
**年代**: [YYYY年 - ファイル名や内容から推定]
**キーパーソン**: [登場する専門家・医師・研究者名をカンマ区切りで]

### 概要
[3-5文で内容を要約。専門用語は一般向けに説明を追加]

### 主要データ・エビデンス
- [数値データや実験結果があれば箇条書き]
- [被験者数、測定方法、p値などの統計情報]
- [効果の具体例]
（データがない場合は「特記なし」と記載）

### キーフレーズ（SNS活用可能）
> 「[文書内の印象的な引用文1]」
> 「[文書内の印象的な引用文2]」
（引用は原文のまま）

### SNS活用アイデア
- **Instagram**: [投稿アイデア - 具体的に]
- **note**: [記事アイデア - 具体的に]

---

日本語で出力してください。内容が読み取れない場合は、その旨を記載してください。
"""


def extract_text_from_pdf(file_path: Path) -> str:
    """PDFからテキストを抽出"""
    if PyPDF2 is None:
        return "[PyPDF2がインストールされていません]"

    try:
        text_parts = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n".join(text_parts)
        # 最大文字数制限（トークン制限対策）
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n...[以下省略]..."
        return full_text if full_text.strip() else "[テキスト抽出不可 - スキャンPDFの可能性]"
    except Exception as e:
        return f"[PDF読み取りエラー: {e}]"


def extract_text_from_docx(file_path: Path) -> str:
    """DOCXからテキストを抽出"""
    if Document is None:
        return "[python-docxがインストールされていません]"

    try:
        doc = Document(file_path)
        text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
        full_text = "\n".join(text_parts)
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n...[以下省略]..."
        return full_text if full_text.strip() else "[テキストが空です]"
    except Exception as e:
        return f"[DOCX読み取りエラー: {e}]"


def extract_text(file_path: Path) -> str:
    """ファイルタイプに応じてテキスト抽出"""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in [".docx"]:
        return extract_text_from_docx(file_path)
    elif suffix == ".doc":
        return "[.doc形式は非対応 - .docxに変換が必要]"
    elif suffix == ".txt":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()[:15000]
        except:
            return "[テキスト読み取りエラー]"
    else:
        return f"[非対応ファイル形式: {suffix}]"


def process_file(file_path: Path) -> str:
    """単一ファイルを処理"""
    print(f"処理中: {file_path.name}", end=" ... ", flush=True)

    # テキスト抽出
    content = extract_text(file_path)

    if content.startswith("[") and content.endswith("]"):
        # エラーメッセージの場合
        print(f"スキップ: {content}")
        return f"\n---\n\n## {file_path.name}\n\n**エラー**: {content}\n\n---\n"

    try:
        # GPT-4o-mini に送信（コスト削減）
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": PROMPT_TEMPLATE.format(
                        filename=file_path.name,
                        content=content
                    )
                }
            ],
            max_tokens=1500,
            temperature=0.3
        )

        result = response.choices[0].message.content
        print("完了")

        # API制限対策（1秒待機）
        time.sleep(1)

        return result

    except Exception as e:
        print(f"APIエラー: {e}")
        return f"\n---\n\n## {file_path.name}\n\n**APIエラー**: {str(e)}\n\n---\n"


def process_folder(folder_path: str, output_file: str):
    """フォルダ内の全ファイルを処理"""
    folder = Path(folder_path)

    if not folder.exists():
        print(f"フォルダが見つかりません: {folder_path}")
        return

    # 処理対象ファイル
    files = []
    for ext in ["*.pdf", "*.docx", "*.doc", "*.txt"]:
        files.extend(folder.glob(ext))

    files = sorted(files, key=lambda x: x.name)

    print(f"\n{'='*50}")
    print(f"フォルダ: {folder.name}")
    print(f"ファイル数: {len(files)}")
    print(f"{'='*50}")

    if not files:
        print("処理対象ファイルがありません")
        return

    results = []
    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] ", end="")
        result = process_file(file_path)
        results.append(result)

    # 結果を出力ファイルに追記
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n{'='*60}\n")
        f.write(f"# {folder.name}\n")
        f.write(f"{'='*60}\n\n")
        f.write("\n".join(results))

    print(f"\n完了: {len(files)} ファイルを処理しました")


def main():
    base_dir = Path("/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project")
    process_dir = base_dir / "ChatGPT処理用"
    output_file = base_dir / "資料まとめ_API処理結果.md"

    print("\n" + "="*60)
    print("資料処理スクリプト - OpenAI GPT-4o-mini")
    print("="*60)

    # 出力ファイルを初期化
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 資料まとめ（API処理結果）\n\n")
        f.write("OpenAI GPT-4o-mini による自動処理結果\n")
        f.write(f"処理日時: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    # 処理順序（優先度順）
    folders = [
        "1_学会発表論文",
        "2_体験談推薦文",
        "3_解説原稿",
        "4_協会誌詳細",
        "5_スターライトヒーリング",
        "6_CD_書籍関連",
        "7_メディア掲載",
        "8_体感音響",
        "9_自然音エビデンス",
        "10_その他"
    ]

    # コマンドライン引数でフォルダを指定可能
    if len(sys.argv) > 1:
        folders = sys.argv[1:]
        print(f"指定フォルダのみ処理: {folders}")

    for folder_name in folders:
        folder_path = process_dir / folder_name
        if folder_path.exists():
            process_folder(str(folder_path), str(output_file))
        else:
            print(f"\nスキップ: {folder_name} (フォルダなし)")

    print(f"\n{'='*60}")
    print("全処理完了")
    print(f"出力ファイル: {output_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
