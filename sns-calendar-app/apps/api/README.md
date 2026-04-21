# API

FastAPI の API サービスです。`/health` に加えて、認証API、投稿API、カレンダーAPI、SNSアカウント連携API を提供します。

## セットアップ

```bash
poetry install
poetry run uvicorn app.main:app --reload
poetry run pytest
```

ローカルでは `sns-calendar-app/.env` を基準に読み込みます。`apps/api/.env.example` をコピーして `apps/api/.env` を置いた場合も、同名キーが優先されます。

最低限必要な環境変数:

```bash
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
X_CONSUMER_KEY=
X_CONSUMER_SECRET=
META_APP_ID=
META_APP_SECRET=
OAUTH_REDIRECT_BASE=http://localhost:8000
```

JWT は Supabase の JWKS を使って検証します。追加の `SUPABASE_JWT_SECRET` は不要です。

## 認証API

- `POST /api/auth/signup`: メール/パスワードで新規登録
- `POST /api/auth/login`: メール/パスワードでログイン
- `POST /api/auth/logout`: Bearer token を使ってサインアウト
- `POST /api/auth/refresh`: refresh token でセッション更新
- `GET /api/auth/me`: Bearer token から現在ユーザーの profile を返却

## SNSアカウント連携API

- `POST /api/sns-accounts/connect/x`: X OAuth 1.0a の認可 URL を生成
- `POST /api/sns-accounts/connect/ig`: Instagram OAuth 2.0 の認可 URL を生成
- `GET /api/sns-accounts/callback/x`: X OAuth コールバック
- `GET /api/sns-accounts/callback/ig`: Instagram OAuth コールバック
- `GET /api/sns-accounts`: 現在ユーザーのデフォルト組織に紐づく有効な連携一覧を返却
- `DELETE /api/sns-accounts/{id}`: 対象連携を論理削除 (`is_active=false`)

## OAuth 設定メモ

- X コールバックURL: `http://localhost:8000/api/sns-accounts/callback/x`
- Instagram コールバックURL: `http://localhost:8000/api/sns-accounts/callback/ig`
- OAuth 成功時のリダイレクト先: `http://localhost:8000/settings/sns?connected={platform}&handle={handle}`
- OAuth 失敗時のリダイレクト先: `http://localhost:8000/settings/sns?error={reason}`

ローカル疎通用の例:

```bash
curl -X POST http://localhost:8000/api/sns-accounts/connect/x \
  -H 'Authorization: Bearer <jwt>'

curl -X POST http://localhost:8000/api/sns-accounts/connect/ig \
  -H 'Authorization: Bearer <jwt>'
```

## Publisher サービス

`app/services/publisher/` では、SNS 投稿処理を API 層や Celery から切り離したサービスとして実装します。

- `base.py`: `Publisher` 抽象クラスと共通戻り値 `PublishResult`
- `x_publisher.py`: X OAuth 1.0a で画像アップロードと投稿を行う具象実装
- `orchestrator.py`: `publish_target(target_id)` で `posts` / `post_targets` / `post_media` / `sns_accounts` を読み、対象ターゲットへ投稿して結果を DB に反映

公開シグネチャ:

```python
from app.services.publisher.orchestrator import publish_target

result = publish_target(target_id="00000000-0000-0000-0000-000000000000")
```

実投稿の手動検証手順:

```bash
cd apps/api
poetry install
poetry run pytest tests/services/test_x_publisher.py tests/services/test_publisher_orchestrator.py
poetry run python -c "from app.services.publisher.orchestrator import publish_target; print(publish_target('<target-uuid>'))"
```

- `.env` に `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `X_CONSUMER_KEY`, `X_CONSUMER_SECRET` を設定する
- `sns_accounts.access_token` は `oauth_token:oauth_token_secret` 形式で保存されている必要がある
- `post_media.storage_path` は Phase 1 では公開 HTTP URL 前提
