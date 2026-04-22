# Codexブリーフィング: WEB-026 ホーム画面（シンプルモード）

**作成日**: 2026-04-21
**担当Issue**: WEB-026（Sprint 4 / 工数: 1.5日）
**依存**: WEB-013（カレンダーAPI）、WEB-015（下書き）、WEB-019（設定）
**後続**: WEB-027（通知画面）

---

## タスク概要

ログイン直後の `/` ページを **シンプルモード** ホーム画面として実装する。今日・明日の予約投稿、直近 3 件の下書き、通知・設定への導線、そして「投稿を作る」大ボタンを配置。Pro ユーザー向けのカレンダービューは既存 `/calendar` に残す。

---

## 設計方針

| 項目 | 決定 |
|---|---|
| UI モード切替 | `users.ui_mode = "simple" \| "pro"` に応じてレンダリング | 
| 今日のタスク | `GET /api/calendar?from=today&to=tomorrow` |
| 下書き最新3件 | `GET /api/posts?status=draft&limit=3` |
| クイックアクション | 「投稿を作る」「下書き一覧」「設定」 3 ボタン |
| 空状態 | 「ようこそ」メッセージ + オンボーディングリンク |
| モバイル対応 | 1カラムレイアウト |

---

## スコープ

### 1. `apps/web/src/app/page.tsx` 更新

`useAuthStore` の `user.uiMode` で分岐:
- `simple`: 新ホーム
- `pro`: `/calendar` へリダイレクト（または簡易カレンダー）

Phase 1 は `simple` 固定（すべてのユーザーに新ホーム表示）。UI mode 切替は follow-up。

### 2. 新ホーム構成

```tsx
<div className="space-y-6">
  <WelcomeSection displayName={user.displayName} />
  <QuickActions />
  <TodaysPostsSection posts={todaysPosts} loading={...} />
  <RecentDraftsSection drafts={recentDrafts} />
  <SystemStatusBanner />  {/* SNS未接続警告等 */}
</div>
```

#### WelcomeSection
- 大きな見出し「こんにちは、{displayName}さん」
- 今日の日付 + 天気風アイコン（静的）
- ヘルプマーク `home.welcome`

#### QuickActions
3ボタン: `投稿を作る` → `/create`、`下書き` → `/drafts`、`設定` → `/settings/sns`

#### TodaysPostsSection
- 今日+明日のスケジュール済み投稿リスト
- 投稿内容の先頭 100 文字 + 時刻 + プラットフォーム chip
- 空なら「本日予定はありません」 + 下書き配置リンク

#### RecentDraftsSection
- 最新 3 件の下書きカード（horizontal scroll）
- 「もっと見る」→ `/drafts`

#### SystemStatusBanner
- `fetchSnsAccounts()` で X / IG 接続状態チェック
- 未接続時: 「X/IG アカウントを接続すると自動投稿できます」+ `/settings/sns` リンク
- 全接続済みなら非表示

### 3. 新規コンポーネント

- `apps/web/src/components/home/WelcomeSection.tsx`
- `apps/web/src/components/home/QuickActions.tsx`
- `apps/web/src/components/home/TodaysPostsSection.tsx`
- `apps/web/src/components/home/RecentDraftsSection.tsx`
- `apps/web/src/components/home/SystemStatusBanner.tsx`

### 4. api-client 活用

既存ヘルパー (`fetchPostList`, `getCalendar`, `fetchSnsAccounts`) をそのまま使用。新規 API 追加なし。

### 5. ヘルプテキスト追加

```typescript
"home.welcome": "ここが毎日の起点です。下のボタンから投稿を作るか、カレンダーで予約を確認できます。",
"home.todays_posts": "今日と明日に予約している投稿です。時刻が近いものから順に並びます。",
"home.recent_drafts": "最近の下書きです。カードをクリックすると編集画面が開きます。",
```

### 6. AppHeader 調整

ロゴクリックで `/` に戻るが、`/` 到達時は現在のナビ状態をクリア。特別な変更不要。

### 7. 動作確認

- [ ] ログイン後 `/` に新ホーム表示
- [ ] 今日の予約投稿が時刻順に表示
- [ ] 下書きが 3 件以内で表示
- [ ] X/IG 未接続時に警告バナー表示
- [ ] 全接続済みで警告バナー非表示
- [ ] モバイル（375px 幅）で崩れない
- [ ] ヘルプマーク機能

---

## スコープ外

- ❌ UI mode 切替設定画面（follow-up）
- ❌ 通知バッジ（WEB-027）
- ❌ AI 推薦（Phase 2）
- ❌ 週間統計グラフ（Phase 2）
- ❌ カスタマイズ可能ダッシュボード
- ❌ ダーク/ライトモード切替
- ❌ `/calendar` `/drafts` `/create` の変更

---

## 成果物チェックリスト

- [ ] `apps/web/src/app/page.tsx` 新ホーム実装
- [ ] `apps/web/src/components/home/` 新規 5 コンポーネント
- [ ] `apps/web/src/lib/help-texts.ts` に home.* 追加
- [ ] `pnpm typecheck` / `pnpm lint` / `pnpm build` 成功
- [ ] 既存 Home にあった認証ガード / ログアウト導線維持
- [ ] Tailwind brand colors のみ
- [ ] Finder複製禁止

## コミット指示

- コミットメッセージ: `feat: WEB-026 ホーム画面シンプルモード`
- Co-Authored-By 不要
