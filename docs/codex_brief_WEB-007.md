# Codexブリーフィング: WEB-007 ログイン/サインアップ画面

**作成日**: 2026-04-18
**担当Issue**: WEB-007（Sprint 1 / 工数: 1.5日）
**依存**: WEB-006（コミット済 `4228756`）
**後続ブロック**: Sprint 2 以降のフロントエンド開発全般

---

## タスク概要

Next.js 15 App Router で **ログイン・サインアップ画面** と **認証状態管理** を実装する。WEB-006 で実装した FastAPI 認証API を叩き、セッションを永続化し、保護ルートへのガードを設置する。決定事項#26-27（ミニヘルプ + ヘルプモードトグル）をUIに反映する。

---

## 設計方針

### 状態管理・データフロー

| 層 | 選択 | 根拠 |
|---|---|---|
| APIクライアント | **@hey-api/openapi-ts 生成SDK** (`apps/web/src/generated/`) | WEB-002で整備。型安全。 |
| 認証ストア | **Zustand** | 既に導入予定、軽量、persist middlewareで localStorage 保存可 |
| フォームバリデーション | **zod + react-hook-form** | 型推論と連動、エラー表示楽 |
| セッション永続化 | **localStorage (MVP)** | Phase 1はシンプル優先。Phase 2で httpOnly cookie 検討 |
| ルートガード | **Next.js middleware** | App Router 標準パターン |

### トークンストレージ注意
- localStorage は XSS リスクあり。Phase 1 割り切り。
- `httpOnly cookie` への移行は Phase 2 TODO として記録。

---

## スコープ（WEB-007で実装するもの）

### 1. FastAPI 側: CORS 設定追加

**WEB-006 までは未設定。フロントから叩くために必要。**

`apps/api/app/main.py` に以下を追加:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

本番デプロイ時の allow_origins は環境変数化（`FRONTEND_URL`）して切替可能に。

### 2. フロントエンド依存追加

`apps/web/package.json`:
```json
{
  "dependencies": {
    "react-hook-form": "^7.53.0",
    "@hookform/resolvers": "^3.9.0"
  }
}
```

**備考**: `zod` と `zustand` は WEB-001 で既に追加済み。

### 3. Zustand 認証ストア

`apps/web/src/stores/auth.ts` 新規作成:

```typescript
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  displayName?: string | null;
  uiMode: "simple" | "pro";
  helpModeEnabled: boolean;
  defaultOrgId?: string | null;
}

interface Session {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;  // Unix epoch seconds
}

interface AuthState {
  user: User | null;
  session: Session | null;
  setSession: (user: User, session: Session) => void;
  clear: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      session: null,
      setSession: (user, session) => set({ user, session }),
      clear: () => set({ user: null, session: null }),
      isAuthenticated: () => {
        const s = get().session;
        if (!s) return false;
        return s.expiresAt > Math.floor(Date.now() / 1000);
      },
    }),
    {
      name: "sns-calendar-auth",
      storage: createJSONStorage(() => localStorage),
    }
  )
);
```

### 4. API 呼び出しヘルパー

`apps/web/src/lib/api-client.ts` 新規作成:
- 生成SDK (`@/generated/sdk.gen.ts`) をラップ
- Base URL 設定（環境変数 `NEXT_PUBLIC_API_BASE_URL`、デフォルト `http://localhost:8000`）
- Bearer token 自動付与
- 401 エラー時に refresh_token でリトライ → 失敗ならログアウト

```typescript
// 抜粋
import { client } from "@/generated/client.gen";
import { useAuthStore } from "@/stores/auth";

client.setConfig({
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
});

// 各 request 前に Bearer 付与
client.interceptors.request.use((request) => {
  const token = useAuthStore.getState().session?.accessToken;
  if (token) {
    request.headers.set("Authorization", `Bearer ${token}`);
  }
  return request;
});
```

### 5. `/login` ページ

`apps/web/src/app/login/page.tsx` 新規作成:
- メール + パスワードフォーム
- zod スキーマでバリデーション（min 8, email 形式）
- submit で `/api/auth/login` 呼び出し
- 成功: Zustand store に保存 → `/` へリダイレクト
- 失敗: エラーメッセージ表示（401: パスワード違い、400: メール形式、等）
- 「アカウントをお持ちでない方は登録」リンク → `/signup`
- **ヘルプマーク（`?`）を主要フィールド横に配置**（決定事項#26）

### 6. `/signup` ページ

`apps/web/src/app/signup/page.tsx` 新規作成:
- メール + パスワード + 確認用パスワード + 表示名（任意）
- zod でバリデーション（パスワード一致も）
- submit で `/api/auth/signup` → 成功時に自動ログイン扱い（session があるはず）
- 失敗: エラー表示
- 「既にアカウントをお持ちの方はログイン」リンク → `/login`
- ヘルプマーク配置

### 7. ルートガード middleware

`apps/web/src/middleware.ts` 新規作成:
- 対象ルート: `/calendar`, `/drafts`, `/create` 等（将来追加予定、今は `/` のみ保護）
- 未認証時 → `/login?redirect=<元URL>` へリダイレクト
- 対象外: `/login`, `/signup`

**注意**: Zustand は client-only なので middleware では使えない。middleware では cookie 参照に切り替える必要あり。

**Phase 1 簡易方針**: middleware は導入せず、**クライアント側 `useAuthGuard` hook** で保護:
```typescript
// apps/web/src/hooks/useAuthGuard.ts
export function useAuthGuard() {
  const router = useRouter();
  const isAuth = useAuthStore((s) => s.isAuthenticated());
  useEffect(() => {
    if (!isAuth) router.push("/login");
  }, [isAuth, router]);
}
```
ホームページで使用。middleware 版は Phase 2 で httpOnly cookie 導入時に実装。

### 8. ヘルプモード機構

`apps/web/src/components/HelpMark.tsx` 新規作成:
- モックアップ `design/mockup/index.html` の `.help-mark` を React コンポーネント化
- Props: `topic` (string) — ヘルプ文言キー
- click で Popover 表示
- body に `help-off` クラスがある時は非表示

`apps/web/src/components/HelpModeToggle.tsx`:
- ヘッダー右上ボタン
- クリックで Zustand store の `helpModeEnabled` トグル（DBに永続化は後で）
- body class を同期

ヘルプ文言: `apps/web/src/lib/help-texts.ts`:
```typescript
export const helpTexts: Record<string, string> = {
  "login.email": "登録時のメールアドレスを入力してください。",
  "login.password": "8文字以上で設定したパスワードを入力してください。",
  "signup.email": "有効なメールアドレスを入力してください。確認メールが届きます。",
  "signup.password": "8文字以上、英数字を含めてください。",
  "signup.password_confirm": "上と同じパスワードをもう一度入力してください。",
  "signup.display_name": "サービス内で表示される名前です（省略可）。",
};
```

### 9. `/` (Home) の更新

`apps/web/src/app/page.tsx` 更新:
- ログイン済みなら「こんにちは、{display_name}」表示 + 「ログアウト」ボタン
- 未ログインなら `/login` にリダイレクト（useAuthGuard 使用）
- 既存の UI Package Button / VERSION 表示は維持

### 10. ヘッダーコンポーネント

`apps/web/src/components/AppHeader.tsx` 新規作成:
- SNS Calendar ロゴ
- HelpModeToggle
- ログイン中: ユーザーアバター + ログアウトボタン
- ログイン状態に応じて表示切替

`apps/web/src/app/layout.tsx` に組み込み（ただし /login と /signup では非表示 or minimal表示）。

### 11. テスト（軽量）

**Phase 1 は自動テストを割愛**し、手動検証のみ。Playwright 等の E2E は Sprint 4 で WEB-028 として実施。

動作確認のチェックリスト（Claude のレビュー時に実施）:
- [ ] `/login` 画面が表示される
- [ ] 無効なメール形式でエラー表示
- [ ] 間違ったパスワードで 401 エラー表示
- [ ] 正しいログイン成功 → `/` にリダイレクト、ユーザー名表示
- [ ] `/signup` で新規作成成功 → 自動ログイン状態で `/` 表示
- [ ] ログアウトで `/login` に戻る
- [ ] ヘルプマーク `?` クリックで吹き出し表示
- [ ] ヘルプモード OFF で全 `?` 非表示
- [ ] localStorage にセッション保存されている
- [ ] トークン期限切れ後のアクセスで `/login` にリダイレクト

### 12. README 更新

`sns-calendar-app/apps/web/README.md`（新規 or 更新）:
- 開発起動手順
- 環境変数（`NEXT_PUBLIC_API_BASE_URL`）
- 認証フロー概要

---

## スコープ外（やらないこと）

- ❌ パスワードリセット画面（WEB-006.1 で別途）
- ❌ OAuth（Google/GitHub）ボタン
- ❌ メール確認フロー（Supabase デフォルト依存）
- ❌ httpOnly cookie 認証（Phase 2）
- ❌ Playwright E2E テスト（Sprint 4 / WEB-028）
- ❌ ダッシュボード・カレンダー・下書き画面（Sprint 2）
- ❌ 実際のヘルプ文言全網羅（主要項目のみ、追加は後日）
- ❌ 多言語対応 (i18n)（夏頃予定）

---

## 必須検証コマンド

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# 1. 依存追加
pnpm install

# 2. 型チェック・lint・build
pnpm typecheck
pnpm build
pnpm lint

# 3. 既存テスト維持
cd apps/api
SUPABASE_URL=http://127.0.0.1:54321 \
SUPABASE_ANON_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH \
SUPABASE_SERVICE_ROLE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz \
poetry run pytest

# 4. 手動動作確認
# ターミナル1: uvicorn
cd apps/api
SUPABASE_URL=http://127.0.0.1:54321 \
SUPABASE_ANON_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH \
SUPABASE_SERVICE_ROLE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz \
poetry run uvicorn app.main:app --reload

# ターミナル2: Next.js
cd apps/web
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev

# ブラウザで http://localhost:3000/login を確認
```

---

## 絶対守るべきこと

- **既存の WEB-001〜006 成果物を壊さない**
- **パスワードを console.log しない**（React DevTools でも露出しない）
- **本番Supabase (`msghvqclexpvgkrctxug.supabase.co`) にテストリクエストを送らない** — ローカルで検証
- **CORS allow_origins は `*` にしない**（明示的なドメインリストのみ）
- スコープ外の実装禁止（OAuth・ダッシュボード等）
- **生成物 `apps/web/src/generated/` は編集しない**（自動生成、WEB-002で管理）
- Tailwind + brand colors は WEB-001 のテーマを使用（新規色追加禁止）
- **`next.config.ts` は変更禁止**（既存設定を維持）

---

## 成果物チェックリスト

- [ ] `apps/api/app/main.py` に CORS ミドルウェア追加
- [ ] `apps/web/package.json` に react-hook-form + @hookform/resolvers 追加
- [ ] `apps/web/src/stores/auth.ts` - Zustand 認証ストア
- [ ] `apps/web/src/lib/api-client.ts` - API ラッパー with Bearer 自動付与
- [ ] `apps/web/src/app/login/page.tsx` - ログイン画面
- [ ] `apps/web/src/app/signup/page.tsx` - サインアップ画面
- [ ] `apps/web/src/hooks/useAuthGuard.ts` - ルートガード
- [ ] `apps/web/src/components/HelpMark.tsx`
- [ ] `apps/web/src/components/HelpModeToggle.tsx`
- [ ] `apps/web/src/lib/help-texts.ts`
- [ ] `apps/web/src/components/AppHeader.tsx`
- [ ] `apps/web/src/app/layout.tsx` にヘッダー統合
- [ ] `apps/web/src/app/page.tsx` 更新
- [ ] `apps/web/README.md` 作成・更新
- [ ] `pnpm typecheck / build / lint` 成功
- [ ] 既存pytest (18 tests) 維持
- [ ] 手動動作確認12項目全パス（Claude 側で実施）
- [ ] スコープ外の実装混入なし

---

## コミット指示

- `git add` は明示指定のみ（`git add .` 禁止）
- `.env` 系は絶対コミットしない
- `apps/web/src/generated/` はコミットしない（.gitignore 済）
- コミットメッセージ: `feat: WEB-007 ログイン/サインアップ画面 + ヘルプモード機構`
- Co-Authored-By 不要

---

## 補足: 関連設計ドキュメント

- `design/design/APP_DESIGN_SPEC.md` 決定事項 #26-27（ヘルプシステム）
- `design/mockup/index.html` — UI実装参考（ヘッダー・help-mark スタイル）
- `design/design/IMPLEMENTATION_PLAN.md` セクション5.1（Sprint 1 詳細）

---

## 補足: 環境情報

- Next.js 15 + React 19（App Router）
- Tailwind CSS v3.4
- TypeScript 5.7
- Node 25.2.1（engines warning は無視可）
- pnpm 9.15.9
- ローカル Supabase 稼働中（http://127.0.0.1:54321）
- ローカル FastAPI は手動起動が必要（Codex は pnpm 系と既存 pytest のみ検証）

**Codex 側で動作確認難しい項目**（Claude がブラウザで確認）:
- Playwright 等未導入のため、実際のログイン→リダイレクトはClaudeの手動テストで実施
- Codexは pnpm build / typecheck 通過まで確認すれば十分

---

## 特に注意: Next.js 15 / React 19 の癖

- `use client` directive 必須（useState, useEffect, Zustand等使用するコンポーネントは全て）
- Tailwind: `globals.css` に `@tailwind base/components/utilities` 記述済み、そのまま使う
- `next/navigation` の `useRouter` 使用（`next/router` は Pages Router で使用禁止）
- フォーム: Server Actions 使わず、**全て client-side fetch** で統一（MVP 簡素化）
- Image component は使わない箇所が多い（アバターアイコン等は SVG）
