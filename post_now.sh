#!/bin/bash
# 即時投稿コマンド - X投稿キュー・IG投稿キューの「投稿予約」をすぐに実行
# 使い方:
#   ./post_now.sh        # X + IG 両方投稿
#   ./post_now.sh x      # Xのみ
#   ./post_now.sh ig     # IGのみ
#   ./post_now.sh dry    # ドライラン（実際には投稿しない）

cd "$(dirname "$0")"
source .env 2>/dev/null

platform="${1:-all}"

echo "=== SNS即時投稿 $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""

if [ "$platform" = "dry" ]; then
    echo "[ドライラン] 実際には投稿しません"
    echo ""
    echo "--- X ---"
    python3 x_auto_poster.py --dry
    echo ""
    echo "--- IG ---"
    python3 ig_auto_poster.py --dry
elif [ "$platform" = "x" ]; then
    echo "--- X投稿実行 ---"
    python3 x_auto_poster.py
elif [ "$platform" = "ig" ]; then
    echo "--- IG投稿実行 ---"
    python3 ig_auto_poster.py
else
    echo "--- X投稿実行 ---"
    python3 x_auto_poster.py
    echo ""
    echo "--- IG投稿実行 ---"
    python3 ig_auto_poster.py
fi

echo ""
echo "=== 完了 ==="
