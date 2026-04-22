# 本番環境変数リスト (WEB-029)

Phase 1 の本番運用で使用する環境変数の一覧と投入先。

## 全体構成

| レイヤ | サービス | 役割 |
|---|---|---|
| フロント | Vercel | Next.js (SSR/SSG/CSR) |
| API | Railway (api サービス) | FastAPI / WebSocket |
| ワーカー | Railway (celery-worker) | Celery タスク実行 |
| スケジューラ | Railway (celery-beat) | 予約投稿ポーリング |
| DB | Supabase Cloud | Postgres + Auth + RLS |
| Redis | Railway プラグイン | Celery broker / Pub-Sub |
| 画像ストレージ | Cloudflare R2 | 投稿メディア保存 |
| メール | SMTP (Gmail 等) | 投稿結果通知 |

---

## Vercel (frontend)

すべて **Production Environment** に投入。Preview にも同じ値（URL だけ staging 相当に変える想定）。

| Key | 例 | 用途 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://api-prod.up.railway.app` | API のベース URL（ブラウザ露出） |
| `NEXT_PUBLIC_WS_URL` | `wss://api-prod.up.railway.app` | WebSocket 用（未使用なら省略可） |

> NEXT_PUBLIC_* は **ブラウザに露出**する。シークレットは絶対に入れない。

---

## Railway (api / celery-worker / celery-beat 共通)

3 サービス全部に同じシークレットを流し込む（Railway の Shared Variables か、各サービスで重複設定）。

### Supabase

| Key | 取得元 |
|---|---|
| `SUPABASE_URL` | Supabase Project Settings → API |
| `SUPABASE_ANON_KEY` | 同上 (publishable) |
| `SUPABASE_SERVICE_ROLE_KEY` | 同上 (secret) |

### OAuth

| Key | 取得元 |
|---|---|
| `X_CONSUMER_KEY` | X Developer Portal |
| `X_CONSUMER_SECRET` | 同上 |
| `META_APP_ID` | Meta for Developers |
| `META_APP_SECRET` | 同上 |
| `OAUTH_REDIRECT_BASE` | `https://api-prod.up.railway.app` （末尾スラッシュなし） |

### Cloudflare R2

| Key | 取得元 |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare Dashboard → R2 |
| `R2_ACCESS_KEY_ID` | R2 API Token |
| `R2_SECRET_ACCESS_KEY` | 同上 |
| `R2_BUCKET_NAME` | バケット名 |
| `R2_PUBLIC_URL` | `https://cdn.example.com/media` （パブリック配信 URL） |

### SMTP (メール通知)

| Key | 例 |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USER` | `no-reply@example.com` |
| `SMTP_PASSWORD` | App password |
| `SMTP_FROM_ADDRESS` | `no-reply@example.com` |

未設定時は通知を no-op でスキップ（投稿本体は成功）。

### Celery / Redis

| Key | 例 |
|---|---|
| `REDIS_URL` | Railway Redis プラグインが自動注入 |
| `CELERY_BROKER_URL` | `${{Redis.REDIS_URL}}` で参照 |
| `CELERY_RESULT_BACKEND` | 同上 |

### FastAPI ミドルウェア

| Key | 例 |
|---|---|
| `FRONTEND_URL` | `https://<project>.vercel.app` |
| `ALLOWED_ORIGINS` | `https://<project>.vercel.app,https://<custom>.com` （カンマ区切り、任意） |
| `ENVIRONMENT` | `production` |
| `APP_NAME` | `SNS Calendar API` |

---

## GitHub Actions シークレット

| Key | 用途 |
|---|---|
| `VERCEL_TOKEN` | `deploy-frontend.yml` |
| `VERCEL_ORG_ID` | 同上 |
| `VERCEL_PROJECT_ID` | 同上 |
| `RAILWAY_TOKEN` | `deploy-backend.yml` |
| `RAILWAY_PROJECT_ID` | 同上 |
| `RAILWAY_ENVIRONMENT` | 同上（通常 `production`） |
| `E2E_SUPABASE_URL` | `e2e.yml`（opt-in） |
| `E2E_SUPABASE_ANON_KEY` | 同上 |
| `E2E_SUPABASE_SERVICE_ROLE_KEY` | 同上 |

### Variables (シークレットでないフラグ)

| Key | 用途 |
|---|---|
| `VERCEL_ENABLED` | `true` にするとフロントデプロイが動く |
| `RAILWAY_ENABLED` | `true` にするとバックエンドデプロイが動く |

トークンを投入する前は両方とも未設定。これにより CI は noop で止まる（誤起動防止）。

---

## Supabase Cloud

| 項目 | 値 |
|---|---|
| Project | `sns-calendar-prod` |
| Region | `ap-northeast-1` (東京) |
| Auth confirm email | Phase 1 は OFF（運用開始後に ON へ） |
| Migrations | `supabase db push` で反映 |
| RLS | 全テーブルで有効化確認 |

---

## OAuth コールバック URL 登録

本番 URL が確定したら以下を登録:

| サービス | URL |
|---|---|
| X Developer Portal | `https://api-prod.up.railway.app/api/sns-accounts/callback/x` |
| Meta for Developers | `https://api-prod.up.railway.app/api/sns-accounts/callback/ig` |

`OAUTH_REDIRECT_BASE` もこれに合わせる。

---

## ロールバック

| 対象 | 手順 |
|---|---|
| フロント | Vercel Dashboard → Deployments → 旧デプロイの **Promote to Production** |
| API | Railway Dashboard → Deployments → 旧リビジョンの **Redeploy** |
| DB | `supabase migration repair` / `supabase db reset`（極力避ける。`supabase db dump` で取ったバックアップから部分復旧） |

破壊的マイグレーションは `supabase/migrations/*` を新しいタイムスタンプで前進させる前方互換方針。
