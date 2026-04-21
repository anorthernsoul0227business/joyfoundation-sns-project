#!/bin/bash
# 自動投稿 launchd 起動スクリプト
# 15分毎に IG/X 両方の auto_poster を順次実行

set -eo pipefail
cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOG_DIR}"

TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[${TS}] === 自動投稿チェック開始 ===" >> "${LOG_DIR}/launchd_runner.log"

/usr/bin/python3 "${PROJECT_DIR}/ig_auto_poster.py" >> "${LOG_DIR}/launchd_runner.log" 2>&1 || true
/usr/bin/python3 "${PROJECT_DIR}/x_auto_poster.py" >> "${LOG_DIR}/launchd_runner.log" 2>&1 || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 自動投稿チェック完了 ===" >> "${LOG_DIR}/launchd_runner.log"
