# 予約投稿 信頼性設計書

**作成日**: 2026-04-16
**関連**: APP_DESIGN_SPEC.md セクション13 優先アクション#2

---

## 1. 設計目標

| 目標 | 基準 |
|---|---|
| 投稿成功率 | 99.5%以上（API側障害を除く） |
| 時間精度 | 予約時刻から±2分以内に投稿開始 |
| 重複投稿 | 0件（冪等性で担保） |
| 障害復旧 | 自動リトライで72時間以内に再実行 |
| データ損失 | 0件（投稿データはDB永続化） |

---

## 2. 投稿ライフサイクル（状態遷移）

```
                  ┌──────────┐
                  │  draft    │  ← 下書き作成
                  └────┬─────┘
                       │ schedule (D&D or 手動)
                       ▼
                  ┌──────────┐
          ┌──────│ scheduled │  ← カレンダーに配置済み
          │      └────┬─────┘
          │           │ 予約時刻到達 (Celery beat)
   unschedule         ▼
          │      ┌──────────┐
          │      │ queued    │  ← ジョブキューに投入
          │      └────┬─────┘
          │           │ worker がピック
          │           ▼
          │      ┌──────────┐
          │      │publishing│  ← API呼び出し中
          │      └──┬───┬───┘
          │         │   │
          │    成功  │   │ 失敗
          │         ▼   ▼
          │   ┌─────┐ ┌────────┐
          │   │publi│ │ failed │
          │   │shed │ └───┬────┘
          │   └─────┘     │ 自動リトライ (≤ max_retries)
          │               ▼
          │         ┌──────────┐
          │         │ retrying │ → queued に戻る
          │         └──────────┘
          │               │ max_retries超過
          │               ▼
          │         ┌──────────┐
          └────────→│  dead    │  ← DLQ（手動対応必要）
                    └──────────┘
```

### PostTarget 単位の状態

各投稿(Post)は複数のPostTargetを持つ（X用、IG用など）。
状態遷移は **PostTarget単位** で管理する。

```
Post.status は PostTarget の集約:
  - 全target published → Post.status = published
  - 1つでも failed/dead → Post.status = partially_failed
  - 全target dead → Post.status = failed
```

---

## 3. 冪等性（Idempotency）設計

### 3.1 問題

同じ投稿が2回以上実行されると、SNS上に重複投稿が出る。
原因: worker crash → リトライ、ネット��ークタイムアウト後の再実行など。

### 3.2 解決策: 冪等キー

```python
# PostTarget テーブルに追加
idempotency_key: str  # uuid v4, 投稿作成時に生成
last_attempt_at: datetime
attempt_count: int
```

**フロー:**
1. ジョブ開始時に `idempotency_key` をチェック
2. 同じキーで `platform_post_id` が既にセットされて���れば → スキップ（成功済み）
3. `last_attempt_at` が直近5分以内なら → スキップ（並行実行防止）
4. `attempt_count` を +1 して実行開始

### 3.3 API側の冪等性

| プラットフォーム | API冪等性サポート | 対策 |
|---|---|---|
| X (Twitter) | なし | テキスト+時刻ハッシュ��重複検知。投稿前に直近投稿を取得して一致チェック |
| Instagram | な��（container_idで部分的に） | container作成→publish を分離。container_idを記録して再利用 |
| YouTube | なし | アッ���ロード前にタイトル+説明で検索。upload_id利用 |
| LINE | なし | message_id をアプリ側で管理 |

---

## 4. リトライ戦略

### 4.1 エラー分���

| カテゴリ | HTTPステータス | リトライ | 例 |
|---|---|---|---|
| **一時的エラー** | 429, 500, 502, 503, 504 | ✅ する | レート制限、サーバー���ウン |
| **認証エラー** | 401, 403 | ❌ しない | トークン期限切れ → 通知して手動対応 |
| **クライアントエラー** | 400 | ❌ しない | 不正なパラメータ → DLQへ |
| **ネットワークエラー** | N/A (timeout) | ✅ する | 接続タイムアウト |

### 4.2 リトライパラメータ

```python
RETRY_CONFIG = {
    'max_retries': 5,
    'initial_delay_sec': 60,        # 1分
    'max_delay_sec': 3600,          # 1時間
    'backoff_factor': 2,            # 指数バックオフ
    'jitter': True,                 # ランダムジッター追加
}

# リトライ間隔: 1分 → 2分 → 4分 → 8分 → 16分 (+ jitter)
```

### 4.3 レート制限��応

```python
# X API: 投稿 50件/24時間（Basic plan）
# IG API: 投稿 25件/24時間

RATE_LIMIT_CONFIG = {
    'x': {'max_per_day': 50, 'min_interval_sec': 30},
    'instagram': {'max_per_day': 25, 'min_interval_sec': 60},
    'youtube': {'max_per_day': 6, 'min_interval_sec': 300},
}

# worker は投稿前にレート制限カウンターをチェック
# 制限到達 → 次の利用可能時刻まで遅延実行
```

---

## 5. Dead Letter Queue (DLQ)

### 5.1 DLQ投入条件

- `max_retries` 超過
- 認証エラー（401/403）
- クライアントエラー（400 — 修正不能）

### 5.2 DLQの処理

```python
# PostTarget.status = 'dead' になったら:
1. Notification を作成 (type: 'post_failure')
2. メール通知を送信（notifier.py 既存機能）
3. 管理画面の「失敗した投稿」一覧に表示
4. ユーザーが「再実行」ボタンで手動リトライ可能
   → status を 'queued' に戻し、attempt_count をリセット
```

### 5.3 DB設計追加

```sql
ALTER TABLE post_target ADD COLUMN
  idempotency_key UUID NOT NULL DEFAULT gen_random_uuid(),
  attempt_count INT NOT NULL DEFAULT 0,
  max_retries INT NOT NULL DEFAULT 5,
  last_attempt_at TIMESTAMPTZ,
  next_retry_at TIMESTAMPTZ,
  last_error_code TEXT,
  last_error_message TEXT;
```

---

## 6. ジョ���スケジューリング詳細

### 6.1 Celery Beat の役割

```python
# 1分ごとに実行される定期タスク
@celery_app.task
def check_scheduled_posts():
    """予約時刻が到達した投稿をキューに投入"""
    now = datetime.utcnow()
    targets = PostTarget.query.filter(
        PostTarget.status == 'pending',
        PostTarget.post.has(Post.status == 'scheduled'),
        PostTarget.post.has(Post.scheduled_at <= now),
    ).all()

    for target in targets:
        target.status = 'queued'
        db.commit()
        publish_post.delay(target.id)  # Celery タスク投入
```

### 6.2 Worker の実行フロー

```python
@celery_app.task(bind=True, max_retries=5)
def publish_post(self, target_id: str):
    target = PostTarget.get(target_id)

    # 1. 冪等チェック
    if target.platform_post_id:
        return  # 既に成功済み

    if target.last_attempt_at and (now - target.last_attempt_at).seconds < 300:
        return  # 並行実行防止

    # 2. レート制限チェック
    if is_rate_limited(target.sns_account.platform):
        self.retry(countdown=next_available_time())
        return

    # 3. 投稿実行
    target.status = 'publishing'
    target.last_attempt_at = now
    target.attempt_count += 1
    db.commit()

    try:
        result = get_publisher(target.sns_account.platform).publish(
            text=target.post.text,
            media=target.post.media,
            account=target.sns_account,
        )
        target.platform_post_id = result.post_id
        target.platform_post_url = result.url
        target.status = 'published'
        target.published_at = now

        # 成功通知
        notify_success(target)

    except RetryableError as e:
        target.last_error_code = e.code
        target.last_error_message = str(e)
        target.status = 'retrying'
        target.next_retry_at = calculate_next_retry(target.attempt_count)
        db.commit()
        self.retry(exc=e, countdown=target.next_retry_at - now)

    except FatalError as e:
        target.last_error_code = e.code
        target.last_error_message = str(e)
        target.status = 'dead'
        db.commit()
        notify_failure(target)

    db.commit()
    update_post_aggregate_status(target.post)
```

---

## 7. 監視・アラート

### 7.1 メトリクス

| メトリクス | 閾値 | アラート先 |
|---|---|---|
| DLQ件数 | > 0 | 管理者メール |
| 投稿成功率 (24h) | < 95% | 管理者メール |
| worker稼働数 | = 0 | 管理者メール（緊急） |
| ジョブ遅延 (scheduled_at - published_at) | > 10分 | ログ警告 |
| キュー滞留数 | > 100 | 管理者メール |

### 7.2 ログ設計

```
[INFO]  publish_post target={id} platform=x status=publishing attempt=1
[INFO]  publish_post target={id} platform=x status=published post_id=12345 latency=3.2s
[WARN]  publish_post target={id} platform=ig status=retrying error=429 next_retry=2026-04-16T19:05:00Z
[ERROR] publish_post target={id} platform=x status=dead error=401 message="Token expired"
```

---

## 8. テスト戦略

| テスト種別 | 対象 | 方法 |
|---|---|---|
| 単体テスト | 冪等チェック、リトライ計算、状態遷移 | pytest + mock |
| 統合テスト | Celery worker → DB → 通知 | pytest + testcontainers (Redis, Postgres) |
| E2Eテスト | 投稿作成 → 予約 → 自動投稿 | sandbox APIキー使用 |
| 障害テスト | worker kill → リトライ → 成功 | chaos engineering (手動) |
| 負荷テスト | 100件同時予約 → 順次実行 | locust |

---

## 9. 既存スクリプトからの移行パス

```
現在                              Phase 1 アプリ
────────���────                    ──────────────
ig_auto_poster.py                → services/publisher/ig_publisher.py
  post_single_image()            → IgPublisher.publish_single()
  post_carousel()                → IgPublisher.publish_carousel()
  prepare_image_url()            → services/media_processor.py

x_auto_poster.py                 → services/publisher/x_publisher.py
  post_tweet()                   → XPublisher.publish()
  upload_image_to_x()            → XPublisher._upload_media()

notifier.py                      → services/notifier.py（ほぼそのまま）
  GmailChannel                   → channels/gmail.py
  (将来) LineChannel             → channels/line.py

Google Sheets連携               → PostgreSQL + API
  投稿キュー読み込み             → POST /api/posts + DB
  ステータス更新                 → DB直接更新
```
