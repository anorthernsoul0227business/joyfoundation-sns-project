#!/bin/bash
# 週次記事生成ループの起動係（Mac mini 用）
#
# launchd から直接 python を呼ばず、この薄い層を挟んでいる理由:
#
#   1. claude CLI の認証トークンを渡すため。plist に直書きすると、設定を
#      いじるたびに秘密が増える。トークンの置き場は ~/agent/.claude-token
#      の1箇所に保ち、ここで環境変数に読み込む。
#   2. 失敗を記録に残すため。launchd は落ちた事実しか残さないので、
#      いつ started/ended したか、終了コードは何かをログに書く。
#
# トークンの種別に注意。sk-ant-oat01- で始まるのは OAuth トークンなので、
# ANTHROPIC_API_KEY ではなく CLAUDE_CODE_OAUTH_TOKEN に入れる。
# 前者に入れると 401 で落ちる（2026-09-01 に実際に踏んだ）。

set -uo pipefail

LOOP="$HOME/agent/loop"
LOG="$LOOP/logs/launchd_runner.log"
TOKEN_FILE="$HOME/agent/.claude-token"

mkdir -p "$LOOP/logs"

say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

say "=== 週次生成 開始 ==="

if [ ! -r "$TOKEN_FILE" ]; then
  say "中止: $TOKEN_FILE が読めない。claude setup-token でトークンを作り直す"
  exit 1
fi
export CLAUDE_CODE_OAUTH_TOKEN="$(cat "$TOKEN_FILE")"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "$LOOP" || { say "中止: $LOOP に入れない"; exit 1; }

# Mac mini はスリープを切ってあるが、OS 側の判断で寝ることがある。
# 生成は数十分かかるので保険をかけておく。
# --test-cards は付けない。
# このフラグは記事IDに TEST- を付け、投稿候補から外す印だった。
# カードの事前承認を求めていた頃の名残で、extract_ac.py も TEST- を
# 承認の証拠から除外する。2026-08-26 に一次承認を康二郎さんへ移し、
# 承認の対象がカードから完成投稿に変わったため、この印は役目を終えた。
# 付けたままだと、生成しても永久に投稿候補にならない。
/usr/bin/caffeinate -ims /usr/bin/python3 run_weekly_loop.py \
  --with-news --topics 3 \
  >> "$LOOP/logs/launchd_stdout.log" 2>> "$LOOP/logs/launchd_stderr.log"
rc=$?

if [ $rc -eq 0 ]; then
  say "=== 週次生成 完了（rc=0）==="
else
  say "=== 週次生成 失敗（rc=$rc）launchd_stderr.log の末尾を見ること ==="
  tail -5 "$LOOP/logs/launchd_stderr.log" | sed 's/^/    /' >> "$LOG"
fi
exit $rc
