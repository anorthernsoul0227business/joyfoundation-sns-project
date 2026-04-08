#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汎用画像リサイズツール - 指定サイズへのリサイズ + 余白パディング

任意の画像を指定サイズにリサイズし、アスペクト比を維持しつつ余白で埋める。
EXIF回転の自動適用、RGBA/P→RGB変換にも対応。

使い方:
  # 基本（4:5 Instagram向け 1080x1350）
  python3 image_resizer.py input.jpg

  # サイズ指定
  python3 image_resizer.py input.jpg --size 1200x630

  # 出力先指定
  python3 image_resizer.py input.jpg -o output.jpg

  # 背景色指定（デフォルト: 白）
  python3 image_resizer.py input.jpg --bg "#F0F0F0"

  # 複数ファイル一括処理
  python3 image_resizer.py img1.jpg img2.png img3.webp --size 1080x1080

  # ディレクトリ内の全画像を処理
  python3 image_resizer.py ./photos/ --size 1080x1350 -o ./resized/

  # JPEG品質指定（デフォルト: 90）
  python3 image_resizer.py input.jpg --quality 95

  # プレビュー（保存せず情報のみ表示）
  python3 image_resizer.py input.jpg --info
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image, ImageOps

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}

# プリセットサイズ
PRESETS = {
    'ig-portrait': (1080, 1350),   # Instagram 4:5
    'ig-square': (1080, 1080),     # Instagram 1:1
    'ig-landscape': (1080, 608),   # Instagram 1.91:1
    'ig-story': (1080, 1920),      # Instagram Story 9:16
    'x-post': (1200, 675),         # X(Twitter) 16:9
    'x-header': (1500, 500),       # X ヘッダー
    'og': (1200, 630),             # OGP画像
    'youtube-thumb': (1280, 720),  # YouTube サムネイル
    'a4-landscape': (3508, 2480),  # A4横 300dpi
    'a4-portrait': (2480, 3508),   # A4縦 300dpi
}


def parse_color(color_str):
    """色文字列をRGBタプルに変換"""
    color_str = color_str.strip().strip('"').strip("'")
    if color_str.startswith('#'):
        hex_color = color_str.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    named_colors = {
        'white': (255, 255, 255), 'black': (0, 0, 0),
        'red': (255, 0, 0), 'green': (0, 128, 0), 'blue': (0, 0, 255),
        'transparent': None,
    }
    return named_colors.get(color_str.lower(), (255, 255, 255))


def parse_size(size_str):
    """サイズ文字列またはプリセット名をタプルに変換"""
    if size_str in PRESETS:
        return PRESETS[size_str]
    parts = size_str.lower().replace(',', 'x').split('x')
    if len(parts) != 2:
        raise ValueError(f"サイズは 'WxH' 形式で指定してください: {size_str}")
    return int(parts[0]), int(parts[1])


def resize_with_padding(img, target_w, target_h, bg_color=(255, 255, 255), quality=90):
    """
    画像をアスペクト比を維持して指定サイズにリサイズし、余白をパディングする。

    Args:
        img: PIL Image
        target_w: 目標幅
        target_h: 目標高さ
        bg_color: 背景色 (R, G, B) タプル、またはNone（透明）
        quality: JPEG品質 (1-100)

    Returns:
        PIL Image (リサイズ済み)
    """
    # EXIF回転を適用
    img = ImageOps.exif_transpose(img)

    # 透明背景の場合はRGBA、それ以外はRGB
    if bg_color is None:
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        output_mode = 'RGBA'
    else:
        if img.mode in ('RGBA', 'P'):
            bg = Image.new('RGB', img.size, bg_color)
            if img.mode == 'RGBA':
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        output_mode = 'RGB'

    # アスペクト比を維持してフィット
    img_w, img_h = img.size
    scale = min(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # 余白で中央配置
    if bg_color is None:
        result = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
    else:
        result = Image.new(output_mode, (target_w, target_h), bg_color)

    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    result.paste(img_resized, (offset_x, offset_y))

    return result


def get_output_path(input_path, output_arg, target_w, target_h):
    """出力パスを決定"""
    input_path = Path(input_path)
    if output_arg:
        output_path = Path(output_arg)
        if output_path.is_dir():
            stem = input_path.stem
            ext = input_path.suffix if input_path.suffix.lower() != '.webp' else '.jpg'
            return output_path / f"{stem}_{target_w}x{target_h}{ext}"
        return output_path
    stem = input_path.stem
    ext = input_path.suffix if input_path.suffix.lower() != '.webp' else '.jpg'
    return input_path.parent / f"{stem}_{target_w}x{target_h}{ext}"


def collect_images(paths):
    """パスリストから画像ファイルを収集"""
    images = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                images.extend(path.glob(f'*{ext}'))
                images.extend(path.glob(f'*{ext.upper()}'))
        elif path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(path)
        else:
            print(f"  スキップ: {p} (非対応形式)")
    return sorted(set(images))


def show_info(img_path):
    """画像情報を表示"""
    img = Image.open(img_path)
    img = ImageOps.exif_transpose(img)
    w, h = img.size
    ratio = w / h
    file_size = os.path.getsize(img_path)

    print(f"  ファイル: {img_path}")
    print(f"  サイズ: {w}x{h}")
    print(f"  アスペクト比: {ratio:.2f} ({w}:{h})")
    print(f"  モード: {img.mode}")
    print(f"  ファイルサイズ: {file_size / 1024:.1f} KB")

    # 最適プリセット提案
    print(f"  ---")
    for name, (pw, ph) in PRESETS.items():
        preset_ratio = pw / ph
        if abs(ratio - preset_ratio) < 0.1:
            print(f"  近いプリセット: {name} ({pw}x{ph})")


def main():
    parser = argparse.ArgumentParser(
        description='汎用画像リサイズツール - 余白パディング付き',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
プリセット一覧:
  ig-portrait    1080x1350  Instagram 4:5
  ig-square      1080x1080  Instagram 1:1
  ig-landscape   1080x608   Instagram 1.91:1
  ig-story       1080x1920  Instagram Story 9:16
  x-post         1200x675   X(Twitter) 16:9
  x-header       1500x500   X ヘッダー
  og             1200x630   OGP画像
  youtube-thumb  1280x720   YouTube サムネイル
  a4-landscape   3508x2480  A4横 300dpi
  a4-portrait    2480x3508  A4縦 300dpi

使用例:
  python3 image_resizer.py photo.jpg --size ig-portrait
  python3 image_resizer.py ./photos/ --size 1080x1080 -o ./output/
        """)

    parser.add_argument('inputs', nargs='*', help='画像ファイルまたはディレクトリ')
    parser.add_argument('--size', '-s', default='ig-portrait',
                        help='出力サイズ (WxH or プリセット名、デフォルト: ig-portrait)')
    parser.add_argument('--output', '-o', default=None,
                        help='出力先ファイルまたはディレクトリ')
    parser.add_argument('--bg', default='white',
                        help='背景色 (#RRGGBB or 色名、デフォルト: white)')
    parser.add_argument('--quality', '-q', type=int, default=90,
                        help='JPEG品質 1-100 (デフォルト: 90)')
    parser.add_argument('--info', action='store_true',
                        help='画像情報を表示するのみ（リサイズしない）')
    parser.add_argument('--presets', action='store_true',
                        help='プリセット一覧を表示')

    args = parser.parse_args()

    if args.presets:
        print("プリセット一覧:")
        for name, (w, h) in PRESETS.items():
            print(f"  {name:20s} {w}x{h}")
        return

    # 画像収集
    images = collect_images(args.inputs)
    if not images:
        print("対象画像が見つかりません")
        sys.exit(1)

    # --info モード
    if args.info:
        for img_path in images:
            show_info(img_path)
            print()
        return

    # サイズ・背景色パース
    target_w, target_h = parse_size(args.size)
    bg_color = parse_color(args.bg)

    # 出力ディレクトリ作成
    if args.output and len(images) > 1:
        Path(args.output).mkdir(parents=True, exist_ok=True)

    print(f"リサイズ: {target_w}x{target_h} | 背景: {args.bg} | 品質: {args.quality}")
    print(f"対象: {len(images)}ファイル")
    print()

    for img_path in images:
        try:
            img = Image.open(img_path)
            original_size = f"{img.size[0]}x{img.size[1]}"

            result = resize_with_padding(img, target_w, target_h, bg_color, args.quality)
            output_path = get_output_path(img_path, args.output, target_w, target_h)

            # 保存
            save_kwargs = {}
            if output_path.suffix.lower() in ('.jpg', '.jpeg'):
                save_kwargs = {'quality': args.quality, 'optimize': True}
            elif output_path.suffix.lower() == '.png':
                save_kwargs = {'optimize': True}

            result.save(output_path, **save_kwargs)
            out_size = os.path.getsize(output_path) / 1024
            print(f"  ✅ {img_path.name} ({original_size}) → {output_path.name} ({target_w}x{target_h}, {out_size:.1f}KB)")

        except Exception as e:
            print(f"  ❌ {img_path.name}: {e}")

    print(f"\n完了!")


if __name__ == '__main__':
    main()
