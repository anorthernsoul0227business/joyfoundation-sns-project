# Codexブリーフィング: WEB-029 Vercel + Railway 本番デプロイ

**作成日**: 2026-04-21
**担当Issue**: WEB-029（Sprint 4 / 工数: 1日）
**依存**: WEB-009（CI/CD 基盤）、全 Sprint 機能完了
**後続**: WEB-030（内部運用開始）

---

## タスク概要

フロント (Next.js) を **Vercel**、API (FastAPI) + Celery を **Railway**、DB を **Supabase Cloud** にデプロイし、本番で稼働させる。ドメインは初回 `*.vercel.app` / `*.up.railway.app` で可。

---

## 設計方針

| レイヤ | サービス | 選定理由 |
|---|---|---|
| フロント | Vercel | Next.js 公式推奨、CDN、Edge 対応 |
| API | Railway | FastAPI + Celery worker + beat を同一プロジェクトで |
| DB | Supabase Cloud | 既にローカル CLI で互換 |
| Redis | Railway Redis プラグイン | Celery broker |
| ストレージ | Cloudflare R2 | 既存設定を流用 |
| シークレット | 各プラットフォームの env | ダッシュボード管理 |

---

## スコープ

### 1. Vercel プロジェクト設定

- GitHub リポジトリ連携（`main` ブランチ）
- Root directory: `sns-calendar-app/apps/web`
- Build command: `pnpm install && pnpm build`
- Output directory: `.next`
- Env 変数:
  - `NEXT_PUBLIC_API_BASE_URL`
  - `NEXT_PUBLIC_WS_URL`
- Preview Deployment: PR 自動生成

### 2. Railway プロジェクト設定

3 サービス構成:

#### api サービス (web process)
- Dockerfile: 既存 `apps/api/Dockerfile` 流用
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET`, `X_CONSUMER_KEY/SECRET`, `META_APP_ID/SECRET`, `R2_*`, `OAUTH_REDIRECT_BASE`, `FRONTEND_URL`, `SMTP_*`

#### celery-worker サービス
- 同じイメージ
- Start command: `celery -A app.tasks.celery_app worker --loglevel=info`

#### celery-beat サービス
- 同じイメージ
- Start command: `celery -A app.tasks.celery_app beat --loglevel=info`

#### Redis プラグイン
- Railway が自動で `REDIS_URL` を注入

### 3. Supabase Cloud 設定

- 既存 `sns-calendar-app/supabase/migrations/*` を `supabase db push` で適用
- RLS ポリシー有効化確認
- `auth` 設定: 確認メール OFF（Phase 1 は簡素化）または開発用に ON のまま
- サービスロールキー / anon キーを API / フロントに設定

### 4. デプロイワークフロー

`.github/workflows/deploy-frontend.yml` 新規 / 既存更新:
- `main` push / `workflow_dispatch` で Vercel CLI デプロイ

`.github/workflows/deploy-backend.yml` 新規 / 既存更新:
- Railway CLI でデプロイ

### 5. OAuth コールバックURL更新

本番URL を取得後:
- X 開発者アプリに `https://api-prod.example.com/api/sns-accounts/callback/x` を登録
- Meta アプリに同様にIG用URL登録
- `OAUTH_REDIRECT_BASE` 環境変数を本番値に

### 6. CORS / CSRF 設定

`apps/api/app/main.py` の `allowed_origins` を本番 Vercel URL に更新:
- `https://<project>.vercel.app`
- カスタムドメイン（後で）

### 7. 監視

- Railway 付属 metrics
- Sentry 導入（Phase 2 推奨）
- ログ: Railway logs で閲覧

### 8. README 更新

`sns-calendar-app/README.md` + ルート `README.md` に:
- 本番URL
- デプロイ手順
- 環境変数リスト
- ロールバック手順

---

## スコープ外

- ❌ カスタムドメイン設定
- ❌ Sentry / DataDog 等 APM（Phase 2）
- ❌ CDN キャッシュ詳細設計
- ❌ 自動ロールバック
- ❌ マルチリージョン
- ❌ Kubernetes / GKE（オーバースペック）

## 成果物チェックリスト

- [ ] `.github/workflows/deploy-frontend.yml` 新規/更新
- [ ] `.github/workflows/deploy-backend.yml` 新規/更新
- [ ] `apps/api/Dockerfile` 検証（Railway 向け）
- [ ] `sns-calendar-app/apps/api/railway.json` or `Procfile` (必要なら)
- [ ] `sns-calendar-app/README.md` デプロイ手順追記
- [ ] 本番 env 変数リスト（`docs/ENV_VARS.md` 新規）
- [ ] Vercel / Railway / Supabase 実際にデプロイして動作確認

## コミット指示

- コミットメッセージ: `chore: WEB-029 Vercel + Railway 本番デプロイ基盤`
- Co-Authored-By 不要

**注意**: このIssueの実作業は Claude 側で手動実行する部分が多い（Vercel/Railway/Supabase のプロジェクト作成・連携・env投入等）。Codex はワークフロー YAML、Dockerfile、ドキュメント整備を担当。
