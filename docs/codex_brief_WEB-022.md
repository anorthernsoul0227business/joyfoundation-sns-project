# Codexブリーフィング: WEB-022 Celery予約投稿タスク

**作成日**: 2026-04-21
**担当Issue**: WEB-022（Sprint 3 / 工数: 2日）
**依存**: WEB-020（X Publisher）、WEB-021（IG Publisher）
**参考**:
  - `apps/api/app/tasks/celery_app.py` / `scheduled_posts.py` (WEB-008)
  - `apps/api/app/services/publisher/orchestrator.py` (WEB-020)
**後続**: WEB-023 (通知), WEB-027 (リアルタイム通知), WEB-028 (E2E)

---

## タスク概要

Celery ワーカー + Beat スケジューラで **予約投稿の自動発火** を実装する。既存の placeholder `check_scheduled_posts` ビートタスクを実装に差し替え、`posts.status='scheduled' AND scheduled_at <= now` を検出して `publish_post(post_id)` タスクを enqueue する。`publish_post` は対象の `post_targets` を順に `publish_target` (WEB-020) で処理する。

既存 `run_both_posters.py` / launchd で動く方式（Google Sheets ベース）を Webアプリ版で置き換える前段階の Issue。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| 発火頻度 | Celery Beat で **1分毎** | 既存 launchd が15分毎だが、Webアプリ版はよりリアルタイム性を上げる |
| 検出クエリ | `posts` に `status='scheduled' AND scheduled_at <= now - interval '0s'` | 時刻到来分を取得 |
| 二重発火防止 | `posts.status='scheduled' → 'publishing'` を 先に UPDATE（conditional WHERE `status='scheduled'`）してから enqueue | race condition 対策 |
| publish_post の冪等性 | `post_targets` レベルで `status != 'published'` のものだけ処理 | orchestrator 側で既処理対応済 |
| 失敗時リトライ | **Phase 1 では手動リトライのみ**（自動リトライなし） | タスク内で try/except し `post_targets.status='failed'` に記録 |
| 全失敗時の親 posts | 全 `post_targets.status='failed'` なら `posts.status='failed'` | orchestrator 側で対応 |
| 一部成功 | `posts.status` は `failed` にも `published` にもしない → **'scheduled' のまま?** いや Phase 1 は **失敗があれば `failed` に寄せる**、成功のみなら `published`。混在は `published` にしない | UI で明示したい |
| ログ | 機微情報なし、post_id / target_id / tweet_id / ig_post_id 程度 | |

### 状態遷移

```
posts.status:
  draft → scheduled  (WEB-012 schedule API)
  scheduled → publishing (check_scheduled_posts で検出時)
  publishing → published / failed (publish_post 完了時)

post_targets.status:
  pending → publishing (orchestrator 内)
  publishing → published / failed
```

---

## スコープ（WEB-022で実装するもの）

### 1. `check_scheduled_posts` 実装

`apps/api/app/tasks/scheduled_posts.py` を刷新:

```python
@celery_app.task(name="app.tasks.scheduled_posts.check_scheduled_posts")
def check_scheduled_posts() -> dict[str, Any]:
    client = get_supabase_client()
    now_iso = datetime.now(UTC).isoformat()
    due_posts = (
        client.table("posts")
        .select("id,org_id")
        .eq("status", "scheduled")
        .lte("scheduled_at", now_iso)
        .limit(50)
        .execute()
        .data
    )
    enqueued: list[str] = []
    for row in due_posts:
        post_id = row["id"]
        # 'scheduled' -> 'publishing' アトミック UPDATE
        updated = (
            client.table("posts")
            .update({"status": "publishing"})
            .eq("id", post_id)
            .eq("status", "scheduled")
            .execute()
            .data
        )
        if updated:
            publish_post.delay(post_id)
            enqueued.append(post_id)
    return {"checked_at": now_iso, "enqueued_count": len(enqueued)}
```

### 2. `publish_post` タスク新規

`apps/api/app/tasks/scheduled_posts.py` に追加:

```python
@celery_app.task(name="app.tasks.scheduled_posts.publish_post", bind=True, max_retries=0)
def publish_post(self, post_id: str) -> dict[str, Any]:
    client = get_supabase_client()
    targets = (
        client.table("post_targets")
        .select("id,platform,status")
        .eq("post_id", post_id)
        .execute()
        .data
    )
    results = []
    for target in targets:
        if target["status"] == "published":
            continue
        try:
            result = publish_target(target["id"])
        except Exception as exc:
            result = PublishResult(success=False, platform_post_id=None,
                                   error_message=f"unhandled: {exc}")
            client.table("post_targets").update({
                "status": "failed",
                "error_message": str(exc)[:500],
            }).eq("id", target["id"]).execute()
        results.append({
            "target_id": target["id"],
            "platform": target["platform"],
            "success": result.success,
            "platform_post_id": result.platform_post_id,
            "error": result.error_message,
        })

    # 親 posts のステータス確定
    final_targets = (
        client.table("post_targets")
        .select("status")
        .eq("post_id", post_id)
        .execute()
        .data
    )
    statuses = {t["status"] for t in final_targets}
    now = datetime.now(UTC).isoformat()
    if statuses == {"published"}:
        parent_status = "published"
        parent_update = {"status": parent_status, "published_at": now}
    elif "failed" in statuses:
        parent_status = "failed"
        parent_update = {"status": parent_status}
    else:
        parent_status = "publishing"  # 未完了な場合はそのまま
        parent_update = None

    if parent_update:
        client.table("posts").update(parent_update).eq("id", post_id).execute()

    return {
        "post_id": post_id,
        "parent_status": parent_status,
        "results": results,
    }
```

- `orchestrator.publish_target` の既存ロジックを再利用
- `max_retries=0` で自動リトライ無効（Phase 1）
- 例外は内部で握り潰し、`post_targets.error_message` に記録

### 3. Beat スケジュール更新

`apps/api/app/tasks/celery_app.py` の `beat_schedule` を「1分毎」に更新:

```python
app.conf.beat_schedule = {
    "check-scheduled-posts": {
        "task": "app.tasks.scheduled_posts.check_scheduled_posts",
        "schedule": 60.0,  # seconds
    },
}
```

既存のコメントアウトまたは placeholder は全削除 / 更新。

### 4. テスト（`apps/api/tests/tasks/test_scheduled_posts.py` 新規）

Celery の eager モード（`task_always_eager=True`）+ Supabase モックで:

- `check_scheduled_posts` が到来済 scheduled を検出して publishing に UPDATE し enqueue（eagerなので即時実行される）
- 条件 UPDATE が race で外れた場合（他ワーカーが先に publishing に変えた）はスキップ
- `publish_post` が未投稿 target のみ処理
- 全 target success → posts.status='published', published_at 設定
- 1 target failed → posts.status='failed'
- 全 target skipped/published (no-op) → posts.status は変えない
- 例外時 target.status='failed', error_message 書込み
- orchestrator は `publish_target` をモックし、success/failure を注入

既存テストが壊れないこと（WEB-008 で placeholder を返していたテストは書き換えが必要な可能性あり → その場合は更新可）。

### 5. ローカル開発手順更新

`apps/api/README.md` に以下を追記:
- Redis 起動（`docker compose up redis`）
- Worker 起動（`poetry run celery -A app.tasks.celery_app worker --loglevel=info`）
- Beat 起動（`poetry run celery -A app.tasks.celery_app beat --loglevel=info`）
- 1分毎にポーリングされるため、1〜2分でテスト投稿が走る

### 6. 既存 placeholder の扱い

- WEB-008 の test ファイル `apps/api/tests/test_celery.py` があれば更新（新しい戻り値に合わせる）
- 既存の `check_scheduled_posts` が返す `{"status": "ok", "checked_at": ...}` は `{"checked_at": ..., "enqueued_count": ...}` に変更

---

## スコープ外（やらないこと）

- ❌ 自動リトライ（Phase 2 で exponential backoff 検討）
- ❌ Dead Letter Queue
- ❌ 通知（成功/失敗 Email / Slack、WEB-023 の範囲）
- ❌ WebSocket でのリアルタイム通知（WEB-027）
- ❌ フロントエンド表示更新
- ❌ レート制限・API 枠管理
- ❌ 大量バッチ対応（Phase 1 は 1分毎 limit 50 で十分）
- ❌ Celery の scale-out / 複数ワーカー想定のロック（Phase 1 は単一ワーカー想定、UPDATE の WHERE 条件で二重発火防止）
- ❌ `pytest-celery` 導入（eager モードのみ利用）
- ❌ 統合E2E（WEB-028 で別 Issue）

---

## 必須検証コマンド

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# pytest（タスクは eager モード）
cd apps/api
poetry run pytest

# ruff
poetry run ruff check .

# ローカル Celery 動作確認（Claude 手動検証）
docker compose up -d redis
poetry run celery -A app.tasks.celery_app worker --loglevel=info &
poetry run celery -A app.tasks.celery_app beat --loglevel=info &
# 予約投稿を1件 scheduled_at=now+10s で作成しログ確認
```

---

## 絶対守るべきこと

- **`publish_target` を壊さない**（WEB-020 既存インターフェース準拠）
- **`get_supabase_client` 経由**のみ DB アクセス
- **Celery task name 変更禁止**（既存 `check_scheduled_posts` 名は維持、追加 `publish_post`）
- **Beat schedule を 1 分毎**、間隔を短縮しない（Redis 負荷配慮）
- **秘密情報をログに書かない**
- **`posts.status='publishing'` への conditional UPDATE で二重発火防止**
- **task_always_eager でテスト**（本番 Celery を起こさない）
- **Finder複製・偽装 shim 禁止**
- **既存 `x_auto_poster.py` / `ig_auto_poster.py` / launchd は触らない**

---

## 成果物チェックリスト

- [ ] `apps/api/app/tasks/scheduled_posts.py` に `check_scheduled_posts` 刷新と `publish_post` 新規追加
- [ ] `apps/api/app/tasks/celery_app.py` の beat_schedule 更新（1分毎）
- [ ] `apps/api/tests/tasks/test_scheduled_posts.py` 新規（6+ケース）
- [ ] 既存 `apps/api/tests/test_celery.py` を新挙動に合わせて更新
- [ ] `apps/api/README.md` にローカル Celery 起動手順追記
- [ ] `poetry run pytest` 全通過
- [ ] `poetry run ruff check .` 全通過
- [ ] `pnpm typecheck` 成功（影響なし）
- [ ] 偽装・Finder複製なし
- [ ] スコープ外の実装混入なし

---

## コミット指示

- `git add` は明示指定のみ
- `.env` / `.celerybeat-schedule` 等のキャッシュはコミット対象外
- コミットメッセージ: `feat: WEB-022 Celery予約投稿タスク（check_scheduled_posts / publish_post）`
- Co-Authored-By 不要（Claude 側で最終コミット時に付与）

---

## 補足: 関連設計ドキュメント / コード

- `design/design/IMPLEMENTATION_PLAN.md` L649 WEB-022 定義
- `design/design/RELIABILITY_DESIGN.md` — 予約投稿の信頼性設計
- `apps/api/app/tasks/celery_app.py` — Celery singleton
- `apps/api/app/services/publisher/orchestrator.py` — `publish_target` (WEB-020)

---

## 補足: 環境情報

- Celery 5.4.0 / Redis 7+
- Python 3.12+ / FastAPI / Supabase
- テストは `task_always_eager=True` で同期実行
- 本番環境では Redis Cloud / Railway Redis を想定

**Codex 側で実施**: タスク実装、テスト、ruff、ドキュメント。
**Claude 側で実施**: `docker compose up redis` + worker/beat 起動、実 scheduled 投稿の動作確認。
