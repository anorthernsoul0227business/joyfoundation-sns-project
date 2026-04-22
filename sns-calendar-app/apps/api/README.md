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
- `ig_publisher.py`: Instagram Graph API の Container ベース投稿を行う具象実装
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
- IG は `sns_accounts.platform_account_id` に IG Business Account ID が保存されている必要がある
- IG は単一画像と 2-10 枚カルーセルに対応する
- IG の `post_media.storage_path` も Phase 1 では公開 `http(s)://` URL 前提
- リール、動画、リポストは Phase 2 対応

## 画像アップロード (WEB-024)

`POST /api/media/upload` は Cloudflare R2 に画像を保存し、`post_media.storage_path` に入れる公開URLを返します。`auto_resize_ig=true` を付けると IG 向けに 4:5 (1080x1350) 白余白パディングを適用します。

必要な環境変数:

```bash
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=https://cdn.example.com/media
```

リクエスト:

```bash
curl -X POST 'http://localhost:8000/api/media/upload?auto_resize_ig=true' \
  -H 'Authorization: Bearer <jwt>' \
  -F 'files=@/path/to/image1.jpg' \
  -F 'files=@/path/to/image2.png'
```

レスポンス（`MediaUploadResponse`）:

```json
{
  "media": [
    {
      "public_url": "https://cdn.example.com/media/post-media/{org_id}/2026/04/22/abc.jpg",
      "storage_path": "post-media/{org_id}/2026/04/22/abc.jpg",
      "width": 1080,
      "height": 1350,
      "mime_type": "image/jpeg"
    }
  ]
}
```

制約:

- 1 枚あたり 10 MB 上限（`413 Request Entity Too Large`）
- リクエスト上限 10 枚（`400 Bad Request`）
- 許容 MIME: `image/jpeg` / `image/png` / `image/webp`
- `auto_resize_ig=true` は常に JPEG で出力（quality=90）
- R2 認証未設定時は `503 Service Unavailable`
- `post_media` テーブルへの書き込みはしない（投稿作成時のフローに任せる）

## 投稿結果メール通知 (WEB-023)

`publish_post` 完了後に `app.services.notifier.notify_post_result` が呼ばれ、対象投稿オーナーの `public.users.email` に結果をメール送信します。Phase 1 は SMTP_SSL のみ対応、送信失敗は warning ログで握り潰し、投稿本体の処理は必ず成功扱いとなります。

必要な環境変数:

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=465            # 省略時は 465
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=no-reply@example.com
```

`SMTP_HOST` または `SMTP_FROM_ADDRESS` 未設定時は送信処理をスキップします（no-op）。

ローカル開発では [Mailpit](https://github.com/axllent/mailpit) / [MailHog](https://github.com/mailhog/MailHog) 等のローカル SMTP サーバを使うと実メールを送らずに動作確認できます。Mailpit 例:

```bash
docker run -d --name mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit
# SMTP_HOST=localhost SMTP_PORT=1025 ... (非SSLのため実運用では推奨しません)
```

単体で呼び出したい場合:

```python
from app.services.notifier import notify_post_result

notify_post_result(
    post_id="...",
    owner_email="owner@example.com",
    summary={
        "success": [{"platform": "x", "platform_post_id": "111"}],
        "failed": [{"platform": "instagram", "error": "token expired"}],
    },
)
```

テストでは `publish_post.run(post_id, notifier=fake_notifier)` で notifier を注入できます。

## Celery 予約投稿

予約投稿の自動発火は Celery worker + beat で動かします。Beat は 1 分ごとに `check_scheduled_posts` を実行し、時刻到来した `posts.status='scheduled'` を `publish_post` に渡します。

ローカル起動手順:

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app
docker compose up -d redis

cd apps/api
poetry run celery -A app.tasks.celery_app worker --loglevel=info
poetry run celery -A app.tasks.celery_app beat --loglevel=info
```

補足:

- テストでは `task_always_eager=True` を使い、実ワーカーは起動しない
- 予約投稿は 1 分ごとにポーリングされるため、テスト用データは 1-2 分以内に発火する
