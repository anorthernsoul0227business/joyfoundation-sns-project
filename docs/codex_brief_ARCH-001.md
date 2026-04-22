# Codexブリーフィング: ARCH-001 Celery Beat → pg_cron + GitHub Actions Cron 移行

**作成日**: 2026-04-22
**担当Issue**: ARCH-001（Sprint ARCH / 工数: 0.5日）
**依存**: なし（Phase 1 MVP の Celery Beat 実装完了が前提）
**参考**: `APP_DESIGN_SPEC.md` Section 15（無料スタック移行計画）
**後続**: ARCH-002（Celery Worker 撤廃）

---

## タスク概要

Celery Beat の予約投稿スケジューリング機能を **Supabase pg_cron + GitHub Actions Cron** に置き換える。Cloud Run への移行（ARCH-004）に先立ち、常駐ワーカーを不要にする。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| スケジューラ | **Supabase pg_cron**（PostgreSQL拡張） | DB 内完結、無料、運用コスト0 |
| 時刻判定 | 毎分 `posts` テーブルから `scheduled_at <= now()` かつ `status = 'scheduled'` を抽出 | 既存 `posts.status` で管理 |
| キュー | 新規テーブル `publish_queue` に INSERT | `locked_at` で排他制御、再試行可能 |
| 実行トリガー | **GitHub Actions Cron**（5分毎）が `POST /internal/publish/flush` を叩く | 既存 `.github/workflows/auto_post.yml` と同パターン |
| 認証 | `X-Internal-Token` ヘッダー（GH Secrets `INTERNAL_API_TOKEN`） | Cloud Run の IAM とは別の内部トークン |
| タイムゾーン | UTC で保存、表示時に JST 変換（既存設計踏襲） | 既存 DB 設計と整合 |

---

## スコープ

### 1. マイグレーション: `publish_queue` テーブル + pg_cron 設定

```sql
-- apps/api/supabase/migrations/YYYYMMDDHHMMSS_publish_queue_pgcron.sql

-- pg_cron 拡張
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA extensions;

-- publish_queue テーブル
CREATE TABLE public.publish_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  scheduled_at TIMESTAMPTZ NOT NULL,
  locked_at TIMESTAMPTZ,
  locked_by TEXT,          -- 'gh-actions' or 'cloud-run'
  attempts INT DEFAULT 0,
  last_error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  CONSTRAINT unique_post_queue UNIQUE (post_id)
);

CREATE INDEX idx_publish_queue_pending ON public.publish_queue
  (scheduled_at) WHERE locked_at IS NULL AND completed_at IS NULL;

-- RLS
ALTER TABLE public.publish_queue ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all" ON public.publish_queue
  FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- pg_cron: 毎分、予約時刻到達の posts を publish_queue に enqueue
SELECT cron.schedule(
  'enqueue-scheduled-posts',
  '* * * * *',
  $$
  INSERT INTO public.publish_queue (post_id, org_id, scheduled_at)
  SELECT id, org_id, scheduled_at
  FROM public.posts
  WHERE status = 'scheduled'
    AND scheduled_at <= NOW()
    AND id NOT IN (SELECT post_id FROM public.publish_queue WHERE completed_at IS NULL)
  ON CONFLICT (post_id) DO NOTHING;
  $$
);
```

### 2. FastAPI エンドポイント: `POST /internal/publish/flush`

`apps/api/app/api/internal.py` 新規作成:

```python
from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Annotated
import os

router = APIRouter(prefix="/internal", tags=["internal"])

async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header()] = None,
):
    expected = os.environ["INTERNAL_API_TOKEN"]
    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Invalid internal token")

@router.post("/publish/flush", dependencies=[Depends(verify_internal_token)])
async def flush_publish_queue(limit: int = 20):
    """publish_queue から pending を取り出し、順次 publish_post を実行"""
    # 1. SELECT ... FOR UPDATE SKIP LOCKED で lock 取得
    # 2. X/IG クライアントで実投稿
    # 3. 成功: completed_at=NOW、失敗: attempts++/last_error
    # 4. 通知 INSERT (Supabase Realtime で受信)
    ...
```

### 3. GitHub Actions Cron

`.github/workflows/publish_flush.yml` 新規作成:

```yaml
name: Publish Flush (Cron)

on:
  schedule:
    - cron: '*/5 * * * *'  # 5分毎
  workflow_dispatch:

jobs:
  flush:
    runs-on: ubuntu-latest
    steps:
      - name: Call API flush endpoint
        env:
          API_URL: ${{ secrets.CLOUD_RUN_API_URL }}
          TOKEN: ${{ secrets.INTERNAL_API_TOKEN }}
        run: |
          curl -sS -X POST "${API_URL}/internal/publish/flush" \
            -H "X-Internal-Token: ${TOKEN}" \
            -H "Content-Type: application/json" \
            --fail
```

### 4. 既存 Celery コード削除は ARCH-002 で実施

このタスクでは **追加のみ**。Celery Beat 設定は ARCH-002 で削除する（並行稼働期間を設けるため）。

---

## テスト計画

- [ ] マイグレーション適用 → `publish_queue` テーブル存在確認
- [ ] pg_cron ジョブ登録確認: `SELECT * FROM cron.job;`
- [ ] `posts` に過去の `scheduled_at` を持つ行を作成 → 1分後に `publish_queue` に入ることを確認
- [ ] `/internal/publish/flush` を curl で叩く → 401 (unauth) / 200 (with token) 応答確認
- [ ] GitHub Actions 手動トリガー → 実投稿まで到達確認（dry-run モード付き）
- [ ] `locked_at` での排他確認: 同時に2回叩いて重複投稿されないこと

---

## リスク

1. **pg_cron のタイムゾーン**: Supabase は UTC 基準。`NOW()` も UTC なので問題なし
2. **5分毎実行の遅延**: GH Actions Cron はベストエフォート（`auto_post.yml` で既知）
3. **Cloud Run コールドスタート**: 5分毎の `/flush` でウォームアップも兼ねる
4. **投稿重複**: `publish_queue.post_id` の UNIQUE 制約 + `SELECT ... FOR UPDATE SKIP LOCKED` で防止

---

## 未決定事項

- [ ] INTERNAL_API_TOKEN の生成方法（`openssl rand -hex 32` で生成し GH Secrets 登録）
- [ ] `publish_queue` の古いレコード削除ポリシー（30日保持後削除の pg_cron ジョブ追加検討）
