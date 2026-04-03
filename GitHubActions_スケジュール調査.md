# GitHub Actions の schedule が動かない問題（調査メモ）

## 結論（要点）
- `workflow_dispatch` が成功しているため、`x_auto_poster.py` の投稿ロジック自体は正常。
- 問題の中心は **GitHub Actions の `schedule` イベント特性**（ベストエフォート実行・遅延/ドロップあり）。
- `schedule` は **デフォルトブランチ上の workflow 定義**のみが対象。別ブランチ変更は自動実行に反映されない。
- 最短間隔は **5分**。1分間隔は不可。

## 本リポジトリで行った改善
- cron を `*/5` から `2-59/5` に変更し、毎時00分を避けて実行。
- 診断ログ（event名、workflow_ref、時刻）を追加し、未実行/遅延の切り分けを容易化。
- `concurrency` を追加し、重複起動による競合を回避。

## 「任意の時間（±5分）」の実現方針
1. GitHub Actions 単体運用（無料・簡単）
   - 5分おきにポーリングして、シート時刻を見て投稿。
   - 遅延/ドロップの可能性を受容する前提。
2. より確実な運用（推奨）
   - 外部スケジューラ（Google Apps Script 時間トリガー / Cloud Scheduler）から
     `repository_dispatch` や API 呼び出しで起動。
   - GitHub `schedule` はバックアップ用途へ。

## コスト目安
- GitHub Actions: Free枠 2,000 分/月（私有リポジトリ、プランに依存）。
  - 5分間隔で24h運用すると、ジョブの平均実行時間次第で上限到達の可能性がある。
- GAS: 無料枠あり（Googleアカウント）。
- Cloud Scheduler: 少額課金（利用量に応じる）。
