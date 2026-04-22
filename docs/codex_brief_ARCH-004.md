# Codexブリーフィング: ARCH-004 FastAPI デプロイ先 Railway → Cloud Run 切替

**作成日**: 2026-04-22
**担当Issue**: ARCH-004（Sprint ARCH / 工数: 0.5日）
**依存**: ARCH-001（pg_cron + publish_queue）、ARCH-002（Celery 削除）、ARCH-003（WebSocket 削除）
**参考**: `APP_DESIGN_SPEC.md` Section 15、既存 `apps/api/Dockerfile`、`.github/workflows/deploy-backend.yml`
**後続**: ARCH-005（Resend 導入）

---

## タスク概要

Celery/Redis 依存を撤廃した FastAPI 単体イメージを **Google Cloud Run**（`asia-northeast1` 東京リージョン、Scale-to-zero）にデプロイする。無料枠内で運用し、固定費 0 円を実現する。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| リージョン | `asia-northeast1`（東京） | 圭一郎さんユーザー層が日本 |
| CPU / メモリ | `1 vCPU / 512 MiB`（最小構成） | FastAPI 単体なら十分 |
| 最小インスタンス | `min-instances=0`（scale-to-zero） | 固定費 0 円 |
| 最大インスタンス | `max-instances=10`（販売化時まで） | Cost 上限制御 |
| タイムアウト | `60秒` | IG container 待機最大値 |
| 認証 | Unauthenticated（公開） + アプリ内で JWT 検証 | Cloud Run IAM は使わない |
| コンテナレジストリ | `Artifact Registry`（`asia-northeast1-docker.pkg.dev`） | GCP 標準 |
| GH→GCP 認証 | **Workload Identity Federation**（Service Account Key 不使用） | セキュアかつ無料 |
| 環境変数 | Cloud Run サービス環境変数 + Secret Manager（機密） | ローテーション容易 |

---

## スコープ

### 1. GCP プロジェクト準備

GCP Console で:
1. プロジェクト作成（`shc-sns-calendar` または既存）
2. 以下 API を有効化:
   - `run.googleapis.com`（Cloud Run）
   - `artifactregistry.googleapis.com`
   - `secretmanager.googleapis.com`
   - `iamcredentials.googleapis.com`
3. Artifact Registry リポジトリ作成: `sns-calendar-api`（asia-northeast1）
4. Secret Manager に機密を登録:
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `INTERNAL_API_TOKEN`
   - `X_CONSUMER_KEY` / `X_CONSUMER_SECRET`
   - `META_APP_ID` / `META_APP_SECRET`
   - `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`
   - `RESEND_API_KEY`（ARCH-005）

### 2. Workload Identity Federation 設定

GitHub Actions から GCP へパスワードレス認証:

```bash
# Workload Identity Pool 作成
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# Provider 作成（GitHub OIDC）
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Service Account 作成＆バインド
gcloud iam service-accounts create github-deployer
gcloud iam service-accounts add-iam-policy-binding \
  github-deployer@<PROJECT>.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/attribute.repository/anorthernsoul0227business/joyfoundation-sns-project"
```

GitHub Secrets に追加:
- `GCP_PROJECT_ID`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`（`projects/<num>/locations/global/workloadIdentityPools/github-pool/providers/github-provider`）
- `GCP_SERVICE_ACCOUNT`（`github-deployer@<PROJECT>.iam.gserviceaccount.com`）

### 3. デプロイワークフロー

`.github/workflows/deploy-backend.yml` を以下で置換:

```yaml
name: Deploy Backend (Cloud Run)

on:
  push:
    branches: [main]
    paths:
      - "sns-calendar-app/apps/api/**"
      - ".github/workflows/deploy-backend.yml"
  workflow_dispatch:

env:
  REGION: asia-northeast1
  SERVICE: sns-calendar-api
  REGISTRY: asia-northeast1-docker.pkg.dev

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write    # Workload Identity Federation
    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker ${{ env.REGISTRY }} --quiet

      - name: Build and Push
        working-directory: sns-calendar-app/apps/api
        run: |
          IMAGE=${{ env.REGISTRY }}/${{ secrets.GCP_PROJECT_ID }}/sns-calendar-api/api:${{ github.sha }}
          docker build -t $IMAGE .
          docker push $IMAGE
          echo "IMAGE=$IMAGE" >> $GITHUB_ENV

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE }} \
            --image=${{ env.IMAGE }} \
            --region=${{ env.REGION }} \
            --platform=managed \
            --allow-unauthenticated \
            --cpu=1 \
            --memory=512Mi \
            --min-instances=0 \
            --max-instances=10 \
            --timeout=60 \
            --set-env-vars="SUPABASE_URL=${{ secrets.SUPABASE_URL }},FRONTEND_URL=${{ secrets.FRONTEND_URL }},R2_ACCOUNT_ID=${{ secrets.R2_ACCOUNT_ID }},R2_BUCKET_NAME=${{ secrets.R2_BUCKET_NAME }},R2_PUBLIC_URL=${{ secrets.R2_PUBLIC_URL }}" \
            --set-secrets="SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,SUPABASE_ANON_KEY=SUPABASE_ANON_KEY:latest,INTERNAL_API_TOKEN=INTERNAL_API_TOKEN:latest,X_CONSUMER_KEY=X_CONSUMER_KEY:latest,X_CONSUMER_SECRET=X_CONSUMER_SECRET:latest,META_APP_ID=META_APP_ID:latest,META_APP_SECRET=META_APP_SECRET:latest,R2_ACCESS_KEY_ID=R2_ACCESS_KEY_ID:latest,R2_SECRET_ACCESS_KEY=R2_SECRET_ACCESS_KEY:latest"
```

### 4. Cloud Run URL を Vercel / GH Secrets に伝播

デプロイ後、URL（`https://sns-calendar-api-<hash>-an.a.run.app`）を取得。

- GH Secret `CLOUD_RUN_API_URL`: `publish_flush.yml`（ARCH-001）から呼ぶ
- Vercel 環境変数 `NEXT_PUBLIC_API_BASE_URL`: フロントから呼ぶ

### 5. Dockerfile 調整

既存 Dockerfile（`apps/api/Dockerfile`）は概ねそのまま利用可。以下だけ確認:

- `EXPOSE 8000` → Cloud Run は `PORT` 環境変数を使うので既存の `${PORT:-8000}` で OK
- `HEALTHCHECK` 不要（Cloud Run 側で `/health` を叩く）

### 6. `apps/api/app/main.py` に `/health` エンドポイント追加

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 7. 削除対象

- `apps/api/railway.json`
- `apps/api/railway.worker.json`（ARCH-002 済）
- `apps/api/railway.beat.json`（ARCH-002 済）

### 8. CORS 設定確認

Cloud Run URL と Vercel URL を CORS 許可リストに追加:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://<vercel-domain>.vercel.app",
        "https://<custom-domain>",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## テスト計画

- [ ] `docker build -t test apps/api && docker run -p 8000:8000 test` でローカル起動成功
- [ ] GH Actions 手動トリガーでデプロイ成功
- [ ] `curl https://<cloud-run-url>/health` → 200 応答
- [ ] `curl https://<cloud-run-url>/internal/publish/flush` → 401（トークンなし）
- [ ] Cold start latency 測定（P50/P95）
- [ ] Web（localhost）から `NEXT_PUBLIC_API_BASE_URL=<cloud-run-url>` で接続 → ログインフロー確認
- [ ] 1時間放置してアイドル → 再リクエスト時のコールドスタート時間確認

---

## リスク

1. **WIF 設定ミス**: 認証エラー時は `gcloud auth print-identity-token` などで切り分け
2. **Secret Manager アクセス権限**: Cloud Run サービスアカウントに `roles/secretmanager.secretAccessor` 必要
3. **Artifact Registry 容量**: 10GB 無料枠、古いイメージを自動削除する Lifecycle Policy 設定推奨
4. **コールドスタート**: 1〜3秒。販売開始後は `min-instances=1` に調整

---

## 完了条件

- [ ] `deploy-backend.yml` push で Cloud Run に自動デプロイ
- [ ] `/health`・`/auth/*`・`/posts`・`/internal/publish/flush` 動作確認
- [ ] GH Secrets に GCP 関連・Cloud Run URL 登録
- [ ] Railway 設定ファイル削除
- [ ] `APP_DESIGN_SPEC.md` Section 15 の未解決事項から関連項目チェック
