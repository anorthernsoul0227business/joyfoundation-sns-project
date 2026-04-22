# Codexブリーフィング: ARCH-002 Celery Worker → FastAPI 内部エンドポイント置換

**作成日**: 2026-04-22
**担当Issue**: ARCH-002（Sprint ARCH / 工数: 0.5日）
**依存**: ARCH-001（pg_cron + publish_queue + /internal/publish/flush 基盤）
**参考**: `APP_DESIGN_SPEC.md` Section 15、既存 `apps/api/app/tasks/scheduled_posts.py`
**後続**: ARCH-004（Cloud Run 移行）

---

## タスク概要

Celery Worker が担っている **投稿実行ロジック** を FastAPI 内部エンドポイントに移植し、Celery 関連コード/設定を削除する。Cloud Run の Scale-to-zero と GH Actions Cron 駆動に移行する前段。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| 実行場所 | `POST /internal/publish/flush` 内で同期実行 | Cloud Run はリクエスト処理中のみ CPU 保証 |
| 並列度 | 1リクエストで最大20件処理（`limit=20`） | 5分/20件/5サイクル = 月12万件まで対応 |
| タイムアウト | Cloud Run 側 60秒 / 1投稿あたり 30秒 | IG Graph API の container 待機を想定 |
| 失敗リトライ | `publish_queue.attempts` で最大3回 | 4回目は `notifications` に failure INSERT |
| ロック | `SELECT ... FOR UPDATE SKIP LOCKED` | pg_cron + GH Actions 同時実行の排他 |
| 削除対象 | `celery_app.py`, `scheduled_posts.py`, `railway.worker.json`, `railway.beat.json`, `pyproject.toml` の celery/redis 依存 | Celery 完全撤廃 |

---

## スコープ

### 1. `apps/api/app/services/publisher.py` に統合

既存 `apps/api/app/tasks/scheduled_posts.py` のロジックを `services/publisher.py` へ移植:

```python
class Publisher:
    def __init__(self, db: Session, notifier: Notifier):
        self.db = db
        self.notifier = notifier

    async def flush_queue(self, limit: int = 20) -> FlushResult:
        """publish_queue から pending を取り出し、投稿を実行"""
        locked = self._lock_pending(limit)
        results = []
        for queue_row in locked:
            try:
                post_id = await self._publish_single(queue_row)
                self._mark_completed(queue_row.id)
                results.append(FlushItem(queue_id=queue_row.id, status="success", post_id=post_id))
            except Exception as e:
                self._mark_failed(queue_row.id, str(e))
                results.append(FlushItem(queue_id=queue_row.id, status="failed", error=str(e)))
        return FlushResult(items=results)

    def _lock_pending(self, limit: int) -> list[PublishQueueRow]:
        """FOR UPDATE SKIP LOCKED で排他取得"""
        ...

    async def _publish_single(self, queue_row) -> str:
        """X or IG クライアントで実投稿 (既存 scheduled_posts.py のロジック移植)"""
        ...
```

### 2. `POST /internal/publish/flush` の実装を完成

ARCH-001 で雛形を作成したエンドポイントを Publisher サービスに接続:

```python
@router.post("/publish/flush", dependencies=[Depends(verify_internal_token)])
async def flush_publish_queue(
    limit: int = 20,
    publisher: Publisher = Depends(get_publisher),
):
    result = await publisher.flush_queue(limit=limit)
    return result
```

### 3. 通知 INSERT への置き換え

旧: Celery タスク完了時に WebSocket で直接送信
新: `notifications` テーブルに INSERT → Supabase Realtime（ARCH-003 で実装）が自動配信

```python
self.db.execute(
    insert(Notification).values(
        user_id=post.user_id,
        org_id=post.org_id,
        kind="post_published" if success else "post_failed",
        title=...,
        body=...,
    )
)
```

### 4. 削除対象ファイル

- `apps/api/app/tasks/celery_app.py`
- `apps/api/app/tasks/scheduled_posts.py`
- `apps/api/app/tasks/__init__.py`
- `apps/api/tests/tasks/test_scheduled_posts.py`
- `apps/api/tests/test_celery.py`
- `apps/api/railway.worker.json`
- `apps/api/railway.beat.json`

### 5. 依存削除

`apps/api/pyproject.toml`:
```toml
# 削除:
# celery = "^5.3"
# redis = "^5.0"
```

`poetry lock --no-update && poetry install` で `poetry.lock` を更新。

### 6. 既存 `/posts/{id}/publish` エンドポイントは残す

即時投稿機能は Celery に依存していないので ARCH-002 では触らない。

---

## テスト計画

- [ ] `publish_queue` に pending 3件を作成 → `/flush` 1回で 3件処理・notifications 3件 INSERT
- [ ] 同時に2回 `/flush` 叩く → `SKIP LOCKED` で重複投稿されない
- [ ] X API 失敗シミュレーション → `attempts` インクリメント・4回目で failure notification
- [ ] `pytest apps/api/tests/` 全パス（削除した test ファイル以外）
- [ ] `poetry install` でエラーなし（celery/redis 依存削除後）

---

## リスク

1. **長時間処理**: IG の container 待機で 30秒超過 → タイムアウト延長 or 非同期化（別途検討）
2. **Celery 削除で既存 `/posts/{id}/publish` 動作確認** → 即時投稿ルートに影響ないことを確認
3. **test_celery.py 削除**: CI で test が減るが、publisher service のテストで代替

---

## 完了条件

- [ ] `pytest` 全パス
- [ ] `pnpm build`（Web 側無関係だが CI で確認）
- [ ] Docker build 成功（`celery` 依存削除後）
- [ ] `/internal/publish/flush` がローカル（docker-compose）で投稿成功
