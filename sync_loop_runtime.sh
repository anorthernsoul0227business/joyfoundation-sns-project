#!/bin/bash
# 週次ループのコードと知識層を、実行機（Mac mini）へ同期する。
#
# なぜ必要か:
#   プロジェクトは ~/Desktop 配下にあり、macOS の TCC（プライバシー保護）により
#   launchd から起動されたプロセスは Desktop 配下のファイルを開けない
#   （Errno 1: Operation not permitted）。そのため実行用のコピーを別に置く。
#
# 2026-09-01、実行機を MacBook から Mac mini へ移した。
#   MacBook はスリープするたびに DNS が死に（Errno 8 nodename nor servname）、
#   生成中の claude も落ちていた（went to sleep mid-response）。
#   Mac mini は24時間起きているのでこれが起きない。
#
# いつ実行するか:
#   - run_weekly_loop.py など Python を変更したとき
#   - カードを追加・修正・削除したとき
#   - 表現ルール・用語集を変更したとき
#
# 実行: ./sync_loop_runtime.sh

set -euo pipefail
PROJECT="/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project"
HOST="kitakoujirou@100.78.122.50"          # Mac mini (Tailscale)
REMOTE="/Users/kitakoujirou/agent/loop"

# Tailscale 越しに 40MB 前後を送る。無指定だと途中で切れるので明示する
# （2026-09-01 に Broken pipe で二度失敗した）
SSH="ssh -o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=8"

echo "同期: $PROJECT → $HOST:$REMOTE"

if ! $SSH "$HOST" true 2>/dev/null; then
  echo "❌ Mac mini に繋がりません。Tailscale が動いているか確認してください" >&2
  exit 1
fi

# ── コード ────────────────────────────────────────────────
# 送るファイルはここに並べる。増えたら足す
SCRIPTS=(
  run_weekly_loop.py    # 本体
  collect_context.py    # --with-news で読み込む
  republish.py          # 投入失敗時の復旧用
  notifier.py           # 重大災害時のメール通知
  image_picker.py       # 記事に添える画像の選定
  supabase_store.py     # 共有ボード（Supabase）への読み書き
  apply_fixes.py        # 圭一郎さんの修正依頼を AI が反映する
  schedule_posts.py     # 承認された記事の投稿日を決め、キューへ渡す
  sync_events.py        # 圭一郎さんのGoogleカレンダーを events に取り込む
  announce_plan.py      # イベント告知の日取りを決める
  generate_event_posts.py  # イベントの告知記事を作る
)
for f in "${SCRIPTS[@]}"; do
  [ -f "$PROJECT/$f" ] || { echo "❌ $f が見つかりません" >&2; exit 1; }
done
rsync -az --partial --timeout=120 -e "$SSH" \
  "${SCRIPTS[@]/#/$PROJECT/}" .env "$HOST:$REMOTE/" 2>/dev/null \
  || { cd "$PROJECT" && rsync -az --partial --timeout=120 -e "$SSH" \
       "${SCRIPTS[@]}" .env "$HOST:$REMOTE/"; }

# ── 知識層 ────────────────────────────────────────────────
# 旧版はここで `rm -rf knowledge` してから cp していた。コピーが途中で
# 止まると全損する作りで、2026-09-01 に実際にカード621枚が消えた。
# rsync の --delete なら、送り終わった分だけを見て差分を消すので、
# 途中で切れてもカードは残る。
#
# _extract と _imgcache は中間生成物。実行に要らず、_imgcache は重い
rsync -az --partial --timeout=120 --delete -e "$SSH" \
  --exclude '_extract/' --exclude '_imgcache/' --exclude '.DS_Store' \
  "$PROJECT/knowledge/" "$HOST:$REMOTE/knowledge/"

date +%Y-%m-%dT%H:%M:%S | $SSH "$HOST" "cat > $REMOTE/.synced_at"

# ── 検算 ──────────────────────────────────────────────────
# 層が増えるたびに書き足す方式は漏れる（2026-08-18 に images と voice が
# 届いていなかった）。両側を機械的に数えて突き合わせる。
echo
echo "✅ 転送完了 $(date '+%Y-%m-%d %H:%M:%S')"
printf "   %-14s %6s %6s\n" "層" "手元" "実行機"

layers=$(find "$PROJECT/knowledge" -maxdepth 1 -type d ! -path "$PROJECT/knowledge" \
         -exec basename {} \; | grep -v '^_' | sort)

remote_counts=$($SSH "$HOST" "for d in $REMOTE/knowledge/*/; do \
  printf '%s %s\n' \"\$(basename \$d)\" \"\$(find \$d -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')\"; done")

mismatch=0
for L in $layers; do
  here=$(find "$PROJECT/knowledge/$L" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
  there=$(echo "$remote_counts" | awk -v l="$L" '$1==l {print $2}')
  there=${there:-0}
  mark=""
  if [ "$here" != "$there" ]; then mark="  ← 不一致"; mismatch=1; fi
  printf "   %-14s %6s %6s%s\n" "$L" "$here" "$there" "$mark"
done

if [ "$mismatch" = "1" ]; then
  echo
  echo "❌ 枚数が合いません。もう一度実行してください" >&2
  exit 1
fi

ACTIVE=$(grep -l '^status: active' "$PROJECT"/knowledge/evidence/EV-*.md 2>/dev/null | wc -l | tr -d ' ' || true)
echo
echo "   Evidence のうち承認済み ${ACTIVE}枚"
