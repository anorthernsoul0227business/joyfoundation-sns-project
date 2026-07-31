#!/bin/bash
# 週次ループを launchd 実行用ディレクトリへ同期する。
#
# なぜ必要か:
#   プロジェクトは ~/Desktop 配下にあり、macOS の TCC（プライバシー保護）により
#   launchd から起動されたプロセスは Desktop 配下のファイルを開けない
#   （Errno 1: Operation not permitted）。
#   そのため保護対象外の場所に実行用コピーを置く。既存の sns-poster-runtime と同じ方式。
#
# いつ実行するか:
#   - run_weekly_loop.py を変更したとき
#   - カードを承認した後（sync_approvals.py --apply のあと）
#   - 表現ルール・用語集を変更したとき
#
# 実行: ./sync_loop_runtime.sh

set -euo pipefail
PROJECT="/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project"
RUNTIME="$HOME/joyfoundation-loop-runtime"

mkdir -p "$RUNTIME/logs"
echo "同期: $PROJECT → $RUNTIME"

cp "$PROJECT/run_weekly_loop.py" "$RUNTIME/"
cp "$PROJECT/collect_context.py" "$RUNTIME/"   # --with-news で読み込む
cp "$PROJECT/notifier.py"        "$RUNTIME/"   # 重大災害時のメール通知で読み込む
cp "$PROJECT/.env"               "$RUNTIME/"   # LOOP_NOTIFY_TO などの設定

# 知識層は丸ごと入れ替える（削除されたカードを残さないため）
rm -rf "$RUNTIME/knowledge"
mkdir -p "$RUNTIME/knowledge"
cp -R "$PROJECT/knowledge/evidence"  "$RUNTIME/knowledge/"
cp -R "$PROJECT/knowledge/editorial" "$RUNTIME/knowledge/"
cp "$PROJECT/knowledge/glossary.md"  "$RUNTIME/knowledge/" 2>/dev/null || true

# 同期時刻を記録する。ループ側でこれを見て古さを警告する
date +%Y-%m-%dT%H:%M:%S > "$RUNTIME/.synced_at"

# grep はヒット0件で exit 1 を返す。pipefail で落ちないよう握りつぶす
ACTIVE=$(grep -l '^status: active' "$RUNTIME"/knowledge/evidence/EV-*.md 2>/dev/null | wc -l | tr -d ' ' || true)
TOTAL=$(ls "$RUNTIME"/knowledge/evidence/EV-*.md 2>/dev/null | wc -l | tr -d ' ' || true)
echo "✅ 同期完了: カード ${TOTAL}枚（うち承認済み ${ACTIVE}枚） $(date)"
