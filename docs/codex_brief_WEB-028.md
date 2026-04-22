# Codexブリーフィング: WEB-028 E2Eテスト

**作成日**: 2026-04-21
**担当Issue**: WEB-028（Sprint 4 / 工数: 2日）
**依存**: WEB-022（Celery）、WEB-023（通知）、WEB-027（WebSocket）
**後続**: WEB-029（本番デプロイ）

---

## タスク概要

**Playwright** でエンドツーエンドシナリオを自動化する。「新規ユーザー登録 → ログイン → 投稿作成 → 予約 → Celery 自動投稿 → 通知受信 → 履歴確認」をワンセットで検証する。

---

## 設計方針

| 項目 | 決定 |
|---|---|
| フレームワーク | Playwright @ apps/web/tests/e2e/ |
| モック | X / IG API は `playwright.mock` で応答を固定 |
| バックエンド | ローカル FastAPI + ローカル Supabase + ローカル Redis |
| 実行 | `pnpm --filter @sns-calendar/web test:e2e` |
| CI | GitHub Actions で PR 時に実行（opt-in） |

---

## スコープ

### 1. Playwright セットアップ

```bash
pnpm --filter @sns-calendar/web add -D @playwright/test
pnpm --filter @sns-calendar/web exec playwright install --with-deps chromium
```

`apps/web/playwright.config.ts` 作成:
- baseURL: `http://localhost:3000`
- webServer: `pnpm dev` 自動起動
- apiURL を env 経由で指定

### 2. テストシナリオ

`apps/web/tests/e2e/core-flow.spec.ts`:

```typescript
test("full publish flow", async ({ page, request }) => {
  // 1. Signup
  await page.goto("/signup");
  await page.fill("[name=email]", `e2e-${Date.now()}@test.local`);
  ...
  // 2. Login
  // 3. Create post
  // 4. Schedule for 10s later
  // 5. Wait for Celery publish
  await expect(page.getByText("投稿成功")).toBeVisible({ timeout: 60000 });
  // 6. Notifications page
});
```

### 3. 追加シナリオ

- `auth.spec.ts`: signup / login / logout / 認証失敗
- `drafts.spec.ts`: 下書き作成・検索・削除・複製
- `calendar.spec.ts`: カレンダー表示 / D&D
- `settings-sns.spec.ts`: 接続/切断（OAuth はモック）
- `notifications.spec.ts`: WebSocket リアルタイム受信確認

### 4. モック戦略

- ネットワーク: `page.route` で `api.x.com` / `graph.facebook.com` をキャプチャし固定レスポンス
- Supabase: ローカル CLI (`supabase start`) で起動、各テスト前にマイグレーション適用
- Redis: Docker compose で起動

### 5. CI 統合

`.github/workflows/e2e.yml` 新規:
- Supabase CLI セットアップ
- Redis サービスコンテナ
- uvicorn + celery worker + beat をバックグラウンド起動
- Playwright 実行
- 失敗時に screenshots / traces を Artifact 保存

---

## スコープ外

- ❌ 本番 X/IG API 実投稿（常にモック）
- ❌ 視覚的回帰テスト（Percy 等）
- ❌ パフォーマンステスト（Phase 2 Lighthouse）
- ❌ モバイルブラウザテスト

## 成果物チェックリスト

- [ ] `apps/web/playwright.config.ts`
- [ ] `apps/web/tests/e2e/` 5+ spec ファイル
- [ ] `apps/web/package.json` に `test:e2e` script
- [ ] `.github/workflows/e2e.yml`
- [ ] `apps/api/README.md` に E2E 手順追加
- [ ] ローカルで `pnpm test:e2e` が通る
- [ ] Finder複製禁止、偽装禁止

## コミット指示

- コミットメッセージ: `test: WEB-028 Playwright E2E テスト`
- Co-Authored-By 不要
