# 運用 KPI (WEB-030)

Phase 1 の試験運用期（2 週間）で計測する KPI と目標値。

## 指標一覧

| 指標 | 目標値 | 計測元 | 計測頻度 |
|---|---|---|---|
| 投稿成功率 | **>= 99%** | `posts.status` の集計 | 週次 |
| 通知到達率 | **>= 95%** | `notifications` テーブル + SMTP 送信ログ | 週次 |
| API レスポンス時間 (p95) | **< 500ms** | Railway metrics | 週次 |
| WebSocket 接続安定性 | **切断 < 1 回/時間** | フロント `isConnected` ログ | 目視 |
| 障害件数 | **<= 1 件/月** | インシデント記録 | 月次 |
| ログイン成功率 | **>= 99%** | Supabase Auth logs | 週次 |

## 計測 SQL（Supabase）

### 投稿成功率

```sql
SELECT
  date_trunc('day', created_at) AS day,
  count(*) FILTER (WHERE status = 'published') AS succeeded,
  count(*) FILTER (WHERE status = 'failed') AS failed,
  round(
    100.0 * count(*) FILTER (WHERE status = 'published')
    / NULLIF(count(*) FILTER (WHERE status IN ('published', 'failed')), 0),
    2
  ) AS success_rate_pct
FROM posts
WHERE created_at >= now() - interval '7 days'
GROUP BY day
ORDER BY day DESC;
```

### 通知到達率

```sql
SELECT
  kind,
  count(*) AS total,
  count(read_at) AS read_count,
  round(100.0 * count(read_at) / NULLIF(count(*), 0), 2) AS read_rate_pct
FROM notifications
WHERE created_at >= now() - interval '7 days'
GROUP BY kind;
```

（既読率は参考値。到達率は SMTP 送信成功数 / 送信試行数で別途確認）

### プラットフォーム別失敗分析

```sql
SELECT
  pt.platform,
  pt.last_error,
  count(*) AS occurrences
FROM post_targets pt
WHERE pt.status = 'failed'
  AND pt.updated_at >= now() - interval '7 days'
GROUP BY pt.platform, pt.last_error
ORDER BY occurrences DESC;
```

## 週次レポート テンプレ

```
## 週次レポート YYYY-MM-DD 〜 YYYY-MM-DD

### 投稿
- 投稿試行: N 件
- 成功: N 件（XX.X%）
- 失敗: N 件（XX.X%）
- 失敗内訳: X=N, IG=N

### 通知
- メール送信: N 件
- メール送信失敗: N 件
- WebSocket 配信: N 件

### パフォーマンス
- API p95: XXX ms
- Celery beat 停止時間: 0 分

### 障害
- なし / あり（詳細）

### 次週アクション
- <改善項目 1〜2 件>
```

## Phase 1 合格基準

2 週間の試験運用終了時に以下を満たせば Phase 1 を完了とする:

- 投稿成功率 >= 99% を連続して達成
- Critical 障害（全ユーザー影響）ゼロ
- 運用負荷が日次 10 分以内に収まる

未達の場合は運用改善を優先し、launchd 版との並走を延長する。
