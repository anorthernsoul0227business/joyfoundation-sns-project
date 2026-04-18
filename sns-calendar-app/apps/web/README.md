# SNS Calendar Web

Next.js 15 / React 19 ベースのフロントエンドです。WEB-007 ではログイン、サインアップ、認証状態の永続化、ヘルプモード UI を実装しています。

## 開発起動

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# API
cd apps/api
SUPABASE_URL=http://127.0.0.1:54321 \
SUPABASE_ANON_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH \
SUPABASE_SERVICE_ROLE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz \
poetry run uvicorn app.main:app --reload

# Web
cd ../web
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev
```

## 環境変数

- `NEXT_PUBLIC_API_BASE_URL`: FastAPI のベース URL。未指定時は `http://localhost:8000`

## 認証フロー概要

1. `/login` または `/signup` から FastAPI 認証 API を呼び出します。
2. 返却された `access_token` / `refresh_token` / ユーザー情報を Zustand persist で `localStorage` に保存します。
3. 保護ページでは `useAuthGuard` が期限切れを含む未認証状態を検知し、`/login?redirect=...` へ移動します。
4. 認証 API が `401` を返した場合、`refresh_token` で 1 回だけ再試行し、失敗時はストアをクリアしてログイン画面へ戻します。
5. ヘルプモードはストアで保持し、`body.help-off` クラスと同期して `HelpMark` の表示を切り替えます。
