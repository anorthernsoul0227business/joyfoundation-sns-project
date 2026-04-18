# API

FastAPI の API サービスです。`/health` に加えて、認証API `/api/auth/signup|login|logout|refresh|me` を提供します。

## セットアップ

```bash
poetry install
poetry run uvicorn app.main:app --reload
poetry run pytest
```

認証APIのローカル検証では以下の環境変数が必要です。

```bash
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
```

`SUPABASE_JWT_SECRET` は Supabase の JWT secret です。ローカル環境では `supabase status` の `JWT secret` を使います。

## 認証API

- `POST /api/auth/signup`: メール/パスワードで新規登録
- `POST /api/auth/login`: メール/パスワードでログイン
- `POST /api/auth/logout`: Bearer token を使ってサインアウト
- `POST /api/auth/refresh`: refresh token でセッション更新
- `GET /api/auth/me`: Bearer token から現在ユーザーの profile を返却

JWT は `SUPABASE_JWT_SECRET` を用いて FastAPI 側で `HS256` ローカル検証します。`/api/auth/me` の profile 取得だけ service role client を使用し、それ以外の認証操作は anon client 経由です。
