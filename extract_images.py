#!/usr/bin/env python3
"""
PDF画像抽出スクリプト
協会誌PDFから画像を抽出し、SNS投稿用に整理して保存
"""

import fitz  # PyMuPDF
import os
import sys
import re
from pathlib import Path

def sanitize_filename(name):
    """ファイル名として使えない文字を置換"""
    return re.sub(r'[\\/*?:"<>|]', '_', name)

def extract_images_from_pdf(pdf_path, output_dir):
    """
    PDFから画像を抽出して保存

    Args:
        pdf_path: PDFファイルのパス
        output_dir: 出力先ディレクトリ

    Returns:
        抽出した画像のリスト
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    # PDFファイル名から年とページ情報を抽出
    pdf_name = pdf_path.stem

    # 年を抽出（4桁の数字）
    year_match = re.search(r'(20\d{2}|19\d{2})', pdf_name)
    year = year_match.group(1) if year_match else "unknown"

    # ページ情報を抽出（p2-p3, P4-P5など）
    page_match = re.search(r'[pP](\d+)[-_][pP]?(\d+)', pdf_name)
    if page_match:
        page_info = f"p{page_match.group(1)}-p{page_match.group(2)}"
    else:
        page_info = "full"

    # 年ごとのサブディレクトリを作成
    year_dir = output_dir / year
    year_dir.mkdir(parents=True, exist_ok=True)

    extracted_images = []

    try:
        doc = fitz.open(pdf_path)

        for page_num, page in enumerate(doc):
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    width = base_image["width"]
                    height = base_image["height"]

                    # 小さすぎる画像はスキップ（アイコンなど）
                    if width < 50 or height < 50:
                        continue

                    # ファイル名を生成
                    img_filename = f"{year}_{page_info}_img{img_index + 1:02d}.{image_ext}"
                    img_path = year_dir / img_filename

                    # 画像を保存
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    extracted_images.append({
                        "filename": img_filename,
                        "path": str(img_path),
                        "source_pdf": pdf_name,
                        "width": width,
                        "height": height,
                        "size_kb": len(image_bytes) / 1024
                    })

                except Exception as e:
                    print(f"  警告: 画像抽出エラー (xref={xref}): {e}")
                    continue

        doc.close()

    except Exception as e:
        print(f"エラー: {pdf_path} の処理中にエラー: {e}")
        return []

    return extracted_images

def main():
    # パス設定
    base_dir = Path("/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project")
    pdf_dir = base_dir / "資料"
    output_dir = base_dir / "抽出画像"

    # 出力ディレクトリ作成
    output_dir.mkdir(exist_ok=True)

    # コマンドライン引数でPDFファイルを指定、なければ全PDF処理
    if len(sys.argv) > 1:
        pdf_files = [pdf_dir / f for f in sys.argv[1:]]
    else:
        pdf_files = list(pdf_dir.glob("*.pdf"))

    print(f"=== PDF画像抽出スクリプト ===")
    print(f"対象ファイル数: {len(pdf_files)}")
    print(f"出力先: {output_dir}")
    print()

    total_images = 0
    results = []

    for pdf_file in pdf_files:
        if not pdf_file.exists():
            print(f"スキップ: {pdf_file} (ファイルが見つかりません)")
            continue

        print(f"処理中: {pdf_file.name}")
        images = extract_images_from_pdf(pdf_file, output_dir)

        if images:
            print(f"  → {len(images)}枚の画像を抽出")
            total_images += len(images)
            results.extend(images)
        else:
            print(f"  → 画像なし")

    print()
    print(f"=== 完了 ===")
    print(f"合計: {total_images}枚の画像を抽出")

    # 結果をログファイルに保存
    if results:
        log_path = output_dir / "抽出ログ.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("# 抽出画像一覧\n\n")
            for img in results:
                f.write(f"ファイル名: {img['filename']}\n")
                f.write(f"  元PDF: {img['source_pdf']}\n")
                f.write(f"  サイズ: {img['width']}x{img['height']} ({img['size_kb']:.1f}KB)\n")
                f.write(f"  パス: {img['path']}\n")
                f.write("\n")
        print(f"ログ保存: {log_path}")

if __name__ == "__main__":
    main()
