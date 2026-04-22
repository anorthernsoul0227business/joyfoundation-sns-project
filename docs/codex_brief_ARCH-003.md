# Codexブリーフィング: ARCH-003 Redis PubSub → Supabase Realtime 移行

**作成日**: 2026-04-22
**担当Issue**: ARCH-003（Sprint ARCH / 工数: 0.5日）
**依存**: なし（独立タスク、ARCH-001/002/004 と並行可）
**参考**: `APP_DESIGN_SPEC.md` Section 15、既存 `apps/api/app/api/notifications_ws.py`、`apps/web/src/hooks/useNotifications.ts`
**後続**: ARCH-004（Cloud Run 移行、WebSocket 撤廃済前提）

---

## タスク概要

FastAPI の WebSocket + Redis PubSub で実現している **リアルタイム通知** を **Supabase Realtime**（PostgreSQL 変更ストリーム）に置き換える。Cloud Run は長時間WebSocket接続に適さないため、DB 変更購読型に変更する。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| 通知配信方式 | Supabase Realtime の `postgres_changes` イベント | 無料、認証・RLS と統合、再接続ロジック組込 |
| 購読テーブル | `public.notifications` | 既存 WEB-027 で作成済 |
| 購読条件 | `event=INSERT` かつ `user_id=current_user` | RLS ポリシーと Realtime フィルタ併用 |
| フロント SDK | `@supabase/supabase-js` 2.x | Web に新規導入 |
| 認証 | Supabase Auth の anon + user JWT | API 経由ログイン後に JWT を localStorage 保存 → supabase-js へ |
| 削除対象 | `apps/api/app/api/notifications_ws.py`、`redis-py` 依存、`SUPABASE_REALTIME_URL` 設定 | 不要 |

---

## スコープ

### 1. Supabase 側: Realtime Publication 有効化

Supabase Dashboard → Database → Publications → `supabase_realtime` に `notifications` テーブルを追加。

または SQL で:

```sql
ALTER PUBLICATION supabase_realtime ADD TABLE public.notifications;
```

### 2. RLS ポリシー確認

既存 WEB-027 マイグレーションの以下が有効であること:

```sql
CREATE POLICY "Users can read own notifications"
ON public.notifications FOR SELECT
USING (auth.uid() = user_id);
```

Realtime は SELECT ポリシーを経由するので、これで自分宛てのみ受信可能。

### 3. Web 側: `useNotifications` フック書き換え

`apps/web/src/hooks/useNotifications.ts`:

```typescript
import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import { useAuthStore } from "../stores/auth";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const session = useAuthStore((s) => s.session);

  useEffect(() => {
    if (!session?.access_token) return;

    // JWT を Realtime 認証に渡す
    supabase.realtime.setAuth(session.access_token);

    const channel = supabase
      .channel("notifications")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "notifications",
        },
        (payload) => {
          setNotifications((prev) => [payload.new as Notification, ...prev]);
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [session?.access_token]);

  return { notifications };
}
```

### 4. 環境変数追加（Web）

`apps/web/.env.example` に追加:

```
NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
```

### 5. 削除対象（API）

- `apps/api/app/api/notifications_ws.py`
- `apps/api/app/main.py` の該当ルート登録
- `apps/api/app/services/notifier.py` の Redis PubSub 部分（notifications テーブル INSERT のみ残す）

### 6. 依存変更

- API: `redis-py` 削除（ARCH-002 と重複するが本タスクで先行可）
- Web: `@supabase/supabase-js` 追加

```bash
pnpm --filter @sns-calendar/web add @supabase/supabase-js
```

---

## テスト計画

- [ ] Supabase Realtime Inspector で `notifications` テーブルの変更イベントが流れていることを確認
- [ ] ログイン後、notifications に手動 INSERT → ブラウザで即受信（localStorage の JWT 経由）
- [ ] 別ユーザーの行が INSERT されても受信しない（RLS 確認）
- [ ] 通信切断→再接続で再購読される（supabase-js が自動対応）
- [ ] `pnpm typecheck` / `pnpm build` 成功

---

## リスク

1. **Supabase Realtime 接続数上限**: Free tier で concurrent 200接続 → MAU 数百までは OK
2. **JWT 期限切れ**: 定期的に `setAuth()` を呼び直す or Supabase Auth 側で refresh
3. **既存 WebSocket クライアントとの互換性**: Phase 1 MVP は WebSocket で動作中、ARCH-003 適用後は Realtime 経由に全面切替
4. **ローカル開発**: `supabase start` でローカル Supabase 立ち上げ時も同じ挙動

---

## 完了条件

- [ ] `notifications_ws.py` 削除、FastAPI 側に WebSocket なし
- [ ] Web でリアルタイム通知が Realtime 経由で動作
- [ ] Redis 依存の削除（API）
- [ ] `pnpm build` / `pytest` 成功
