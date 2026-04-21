# Codexブリーフィング: WEB-019 SNSアカウント設定画面

**作成日**: 2026-04-21
**担当Issue**: WEB-019（Sprint 3 / 工数: 1日）
**依存**: WEB-018（コミット済 `e4b5d22` / SNSアカウント連携API）
**後続ブロック**: WEB-020 (X Publisher) / WEB-021 (IG Publisher) で利用する接続済みアカウント一覧の入口

---

## タスク概要

Next.js 15 App Router で **SNSアカウント設定画面** (`/settings/sns`) を実装する。WEB-018 の `/api/sns-accounts/*` を叩いて接続済みアカウントを一覧表示し、「接続」ボタンで認可URLへ遷移、コールバック後の戻り先として成功/失敗バナーを表示、「切断」ボタンで論理削除を行う。

WEB-018 のコールバック (`/api/sns-accounts/callback/{platform}`) は成功時に `{OAUTH_REDIRECT_BASE}/settings/sns?connected={platform}&handle={handle}`、失敗時に `?error={reason}` へ 302 する設計になっている。この画面がその受け皿。

---

## 設計方針

| 層 | 選択 | 根拠 |
|---|---|---|
| APIクライアント | **生成済 SDK** (`apps/web/src/generated/sdk.gen.ts`) | WEB-018で追加済 `connectSnsAccountApiSnsAccountsConnectPlatformPost` / `listSnsAccountsApiSnsAccountsGet` / `deleteSnsAccountApiSnsAccountsAccountIdDelete` をそのまま使う |
| APIラッパー | **`lib/api-client.ts` に追記** | 既存 `fetchPostList` / `createPost` 等と同じパターン。Bearer自動付与・401リフレッシュを流用 |
| 認証ガード | **`useAuthGuard()` フック** | 既存の `/calendar` `/drafts` `/create` と同じ方式 |
| UIレイアウト | **`AppShell` + `AppHeader`** | 他ページと同じ外枠 |
| 成功/失敗通知 | **URLクエリ検出で画面上部バナー** | トースト基盤は未導入。ページ内バナーで簡素に |
| ナビ | **`AppHeader.navItems` に「設定」追加** | 他ページと同列 |

---

## スコープ（WEB-019で実装するもの）

### 1. APIラッパー追加（`apps/web/src/lib/api-client.ts`）

既存パターンに合わせて以下を追記:

```typescript
// 追加 import
import {
  connectSnsAccountApiSnsAccountsConnectPlatformPost,
  deleteSnsAccountApiSnsAccountsAccountIdDelete,
  listSnsAccountsApiSnsAccountsGet,
} from "../generated/sdk.gen";
import type {
  ConnectResponse,
  SnsAccountListResponse,
  SnsAccountSafe,
} from "../generated/types.gen";

// エクスポート
export async function fetchSnsAccounts(): Promise<SnsAccountListResponse> { ... }
export async function connectSnsAccount(platform: "x" | "ig"): Promise<ConnectResponse> { ... }
export async function disconnectSnsAccount(accountId: string): Promise<void> { ... }
```

各関数は:
- `withAuthRetry(async () => ...)` 既存ヘルパーで 401 時に自動リフレッシュ
- `result.error` は `ApiError` に変換してスロー
- 戻り値のネスト（`data` / `error`）は既存 `fetchPostList` 等と同じ扱い

### 2. `/settings/sns` ページ（`apps/web/src/app/settings/sns/page.tsx` 新規）

`"use client"` で作成。他ページと同じ構造:

```tsx
export default function SnsAccountsSettingsPage() {
  useAuthGuard();
  // ローカル state: accounts, loading, error, banner(connected/handle/error_reason), busyAction
  // useEffect で fetchSnsAccounts() → accounts set
  // useSearchParams で ?connected=&handle=& or ?error= 検出 → banner state
  // handleConnect(platform): connectSnsAccount(platform) → window.location.href = authorization_url
  // handleDisconnect(id): confirm dialog → disconnectSnsAccount(id) → 再fetch
  // 表示: バナー、X カード、IG カード（それぞれ接続済みアカウントの一覧 + 接続ボタン）
}
```

#### 画面要素

- **ヘッダー** (`AppShell` 内)
  - 見出し「SNSアカウント連携」
  - 補足文「X と Instagram のアカウントを接続すると、投稿キューから自動投稿できるようになります。」
  - `HelpMark topic="settings.sns"` 付き

- **結果バナー**（URLクエリ由来）
  - 成功: `?connected=x&handle=joy_foundation` → 「✅ @joy_foundation を X に接続しました」緑
  - 失敗: `?error=state_mismatch` → 「⚠️ 接続に失敗しました: state_mismatch」赤
  - 閉じるボタン（内部stateで非表示化、URLは `router.replace('/settings/sns')` でクリーン化）

- **プラットフォームカード**（X / IG 各1枚）
  - プラットフォーム名 + アイコン色（既存 `bg-x` / `bg-ig` クラス）
  - 接続済みアカウント一覧:
    - `@{handle}` / display_name / 接続日時（`created_at`）/ `expires_at` があれば「YYYY/MM/DD まで有効」
    - 「切断」ボタン（確認ダイアログ `window.confirm("...")` 後に削除）
  - 未接続または追加接続用の「接続する」ボタン
    - クリックで `handleConnect(platform)` → サーバ側で発行された `authorization_url` に `window.location.href` で遷移

- **空状態**: アカウントなしのカードは「未接続」表示と「接続する」ボタン

### 3. ナビゲーション追加（`AppHeader.tsx`）

`navItems` に以下を追加:
```typescript
{ href: "/settings/sns", label: "設定", enabled: true },
```

位置は最後（AI生成の右）。将来の設定セクション拡張を見越して `/settings` をベースにするが Phase 1 では `/settings/sns` 直リンクで良い。

### 4. ヘルプテキスト追加（`apps/web/src/lib/help-texts.ts`）

```typescript
"settings.sns": "X (Twitter) や Instagram のアカウントをここで接続します。接続するとカレンダーから自動投稿できるようになります。接続を外すときは「切断」ボタンを押してください。",
```

### 5. 型補助（必要に応じて）

生成型 `SnsAccountSafe` を import して使う。手書きの型定義は最小限。

### 6. 既存ページへの影響

- `apps/web/src/app/page.tsx` (Home) の簡易ダッシュボードに「SNSアカウントを接続する」導線を追加してもよい（optional）。追加する場合は簡素な Link 1 本のみ
- `middleware.ts` は使っていない（クライアント側 useAuthGuard 方式）→ 変更不要

### 7. OpenAPI 再生成

WEB-018 で生成済のため**再生成は不要**。`apps/web/src/generated/` を触らない。

### 8. 動作確認チェックリスト（Claude 側で実施）

- [ ] 未認証で `/settings/sns` → `/login` にリダイレクト
- [ ] 認証済で `/settings/sns` → 空状態の X / IG カード2枚表示
- [ ] 「X を接続する」→ 認可URLに遷移（実 OAuth は X API キー未設定だとサーバ 500 エラー）
- [ ] callback 成功後に `?connected=x&handle=...` で成功バナー表示
- [ ] callback 失敗時に `?error=...` で警告バナー表示
- [ ] 接続済みアカウント表示（@handle / 接続日時）
- [ ] 「切断」ボタン→確認ダイアログ→削除→一覧から消える
- [ ] ヘルプモードONで `?` アイコン表示、OFFで非表示
- [ ] ナビの「設定」リンクで遷移可能

---

## スコープ外（やらないこと）

- ❌ note / YouTube / LINE の接続UI（Phase 2。カードは X/IG の2枚のみ）
- ❌ 実際の X / Meta OAuth アプリ登録・`.env` への鍵投入（ユーザー作業）
- ❌ トークンの有効期限切れ通知・自動リフレッシュ（follow-up）
- ❌ 複数 Facebook Page からの IG Business Account 選択UI（WEB-018 follow-up）
- ❌ トースト通知基盤の導入（画面内バナーで代替）
- ❌ Playwright E2E テスト（Sprint 4 / WEB-028）
- ❌ `/settings` ハブページ（直接 `/settings/sns` のみ）
- ❌ 既存ページ（`/calendar`, `/drafts`, `/create`）の変更（ナビ追加は `AppHeader.tsx` のみ）

---

## 必須検証コマンド

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# 型チェック・lint・build
pnpm typecheck
pnpm lint
pnpm build

# 既存 pytest 維持
cd apps/api && poetry run pytest
```

`pnpm typecheck`, `pnpm lint`, `pnpm build`, `pytest (18 passed / 44 skipped)` が全通過すること。

---

## 絶対守るべきこと

- **CLAUDE.md の Codex CLI Usage 節に従う**: 偽装絶対禁止。新規依存は入れない想定（既存SDK活用のみ）。もし必要なら `pnpm add` で正規インストール
- **`apps/web/src/generated/` は手動編集禁止**（自動生成物。WEB-018時点で最新）
- **既存ページ（`/calendar`, `/drafts`, `/create`, `/login`, `/signup`）の挙動を壊さない**
- **Tailwind クラスは既存 brand colors を使用**（`bg-x`, `bg-ig`, `bg-brand-ocean`, `text-brand-ink` 等）。新規色追加禁止
- **`next.config.ts` は変更禁止**
- **React 19 / App Router の癖**: `"use client"` directive を忘れない。`useSearchParams` / `useRouter` は `next/navigation` から import
- **`access_token` など秘密情報は表示しない**（SnsAccountSafe は安全ビューなので含まれないが、万が一の防御）
- **Finder 複製 `* 2.*` を作らない**
- **`logs/` などプロジェクト外のファイルは触らない**
- **WEB-018 で作った `apps/api/` 側コードは触らない**（ただしAPIに変更を入れたい場合は報告）

---

## 成果物チェックリスト

- [ ] `apps/web/src/lib/api-client.ts` に `fetchSnsAccounts` / `connectSnsAccount` / `disconnectSnsAccount` 追加
- [ ] `apps/web/src/app/settings/sns/page.tsx` 新規（設定画面本体）
- [ ] `apps/web/src/components/AppHeader.tsx` に「設定」ナビ追加
- [ ] `apps/web/src/lib/help-texts.ts` に `settings.sns` キー追加
- [ ] 既存 `apps/web/src/app/layout.tsx` を壊さない
- [ ] `pnpm typecheck` 成功
- [ ] `pnpm lint` 成功
- [ ] `pnpm build` 成功（`/settings/sns` ルートが静的生成に追加される）
- [ ] 既存 pytest 維持（18 passed / 44 skipped）
- [ ] `apps/web/src/generated/` の手動編集なし
- [ ] `* 2.*` Finder 複製なし
- [ ] スコープ外の実装混入なし

---

## コミット指示

- `git add` は明示指定のみ
- `.env` 系はコミット対象外
- `apps/web/src/generated/` はコミット対象外（.gitignore 済）
- コミットメッセージ: `feat: WEB-019 SNSアカウント設定画面`
- Co-Authored-By 不要（Claude 側で最終コミット時に付与する）

---

## 補足: 関連設計ドキュメント

- `design/design/APP_DESIGN_SPEC.md` L490-494 SNSアカウントAPIエンドポイント
- `docs/codex_brief_WEB-018.md` L156-161 コールバックリダイレクトURL仕様（`/settings/sns?connected=...&handle=...`）
- `apps/web/src/app/drafts/page.tsx` 既存クライアントページ実装パターンの参考
- `apps/web/src/components/AppHeader.tsx` ナビ追加箇所

---

## 補足: 環境情報

- Next.js 15 + React 19（App Router）
- Tailwind CSS v3.4（既存 brand colors 使用）
- TypeScript 5.7
- Node 25.2.1
- pnpm 9.15.9
- 生成SDK: `@hey-api/openapi-ts` 由来
- 既存認証ストア: Zustand (`apps/web/src/stores/auth.ts`)

**Codex 側で実施するもの**: コード追加 / typecheck / lint / build。
**Claude 側で実施するもの**: 実ブラウザでの挙動確認（OAuth 実キー投入は別途手動）。

---

## 特に注意: Next.js 15 / App Router の癖

- `"use client"` directive を忘れない
- `useSearchParams` 使用時は `<Suspense>` でラップが推奨されるが、Phase 1 では動けば可
- `window.location.href = authorization_url` での外部遷移は OK（SPA 的な `router.push` は外部URLに使えない）
- `usePathname()` の動的判定で「設定」ナビのアクティブ表示を実装
