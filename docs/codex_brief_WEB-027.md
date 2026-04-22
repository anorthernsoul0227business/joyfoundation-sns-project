# Codexブリーフィング: WEB-027 通知画面 + WebSocket リアルタイム

**作成日**: 2026-04-21
**担当Issue**: WEB-027（Sprint 4 / 工数: 1.5日）
**依存**: WEB-023（メール通知）、WEB-022（publish_post）
**後続**: WEB-028（E2E テスト）

---

## タスク概要

投稿成功/失敗の **リアルタイム通知** を WebSocket で配信し、ヘッダーの通知ベルに未読カウントを表示、`/notifications` ページで履歴を一覧できるようにする。

---

## 設計方針

| 項目 | 決定 |
|---|---|
| バックエンド | FastAPI `WebSocket /ws/notifications`（Bearer auth） + Redis PubSub |
| 通知永続化 | 新規テーブル `notifications` (title, body, kind, read_at, created_at) |
| フロント | 専用 `useNotifications` フック + `NotificationBell` コンポーネント + `/notifications` 一覧 |
| 再接続 | exponential backoff（1s / 2s / 4s / 8s、最大 30s）|
| 通知の発火 | WEB-022 `publish_post` 完了時に WEB-023 `notify_post_result` と並行してWebSocket配信 |
| 認証 | WebSocket 接続時に `?token=...` で JWT を検証 |

---

## スコープ

### 1. マイグレーション: `notifications` テーブル

```sql
CREATE TABLE public.notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  org_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  kind VARCHAR(30) NOT NULL,  -- 'post_published', 'post_failed', 'system'
  title TEXT NOT NULL,
  body TEXT,
  related_post_id UUID REFERENCES public.posts(id) ON DELETE SET NULL,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_user_unread ON public.notifications (user_id, read_at) WHERE read_at IS NULL;

-- RLS: 自 user_id のみ SELECT
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY notifications_user_select ON public.notifications FOR SELECT USING (user_id = auth.uid());
```

### 2. API エンドポイント

| メソッド | パス | 動作 |
|---|---|---|
| GET | `/api/notifications` | ページング可能な通知一覧 |
| POST | `/api/notifications/{id}/read` | 既読マーク |
| POST | `/api/notifications/read-all` | 全既読 |
| WS | `/ws/notifications?token=...` | リアルタイム配信 |

### 3. WebSocket サーバ実装

`apps/api/app/api/notifications_ws.py`:
- FastAPI `WebSocketRoute`
- 接続時 JWT 検証 → user_id 取得
- Redis PubSub channel `notifications:{user_id}` を subscribe
- クライアント ping/pong で heartbeat

### 4. 通知発火

`apps/api/app/services/notifier.py` 拡張:
- `notify_post_result` 内で以下を実行:
  1. DB `notifications` INSERT
  2. Redis `PUBLISH notifications:{user_id} <json>`
  3. SMTP 送信（WEB-023 既存）

### 5. フロント

- `apps/web/src/hooks/useNotifications.ts`: WebSocket 接続・再接続・状態管理
- `apps/web/src/components/NotificationBell.tsx`: 未読カウント赤バッジ、クリックで drawer
- `apps/web/src/app/notifications/page.tsx`: 履歴一覧、既読ボタン
- `AppHeader.tsx` に `NotificationBell` 配置

### 6. テスト

- pytest: `notifications` CRUD、既読、WebSocket 接続/認証
- Playwright: E2E 後回し（WEB-028）

---

## スコープ外

- ❌ Push 通知（ブラウザ Notification API）は Phase 2
- ❌ 通知フィルタ（種別・期間）
- ❌ 通知設定画面（音量、即時/一括）
- ❌ プッシュ通知 Slack 連携

## 成果物チェックリスト

- [ ] `supabase/migrations/YYYYMMDDHHMMSS_notifications.sql`
- [ ] `apps/api/app/api/notifications.py` (REST CRUD)
- [ ] `apps/api/app/api/notifications_ws.py` (WebSocket)
- [ ] `apps/api/app/services/notifier.py` 拡張
- [ ] `apps/web/src/hooks/useNotifications.ts`
- [ ] `apps/web/src/components/NotificationBell.tsx`
- [ ] `apps/web/src/app/notifications/page.tsx`
- [ ] `apps/web/src/components/AppHeader.tsx` 更新
- [ ] pytest 新規 8+件
- [ ] `pnpm typecheck/lint/build` / `pytest` / `ruff` 全通過

## コミット指示

- コミットメッセージ: `feat: WEB-027 通知画面 + WebSocket リアルタイム配信`
- Co-Authored-By 不要
