# GCP Cloud Run セットアップ手順書（ARCH-004 本番デプロイ）

**対象**: `sns-calendar-app/apps/api` の Google Cloud Run デプロイ
**想定所要時間**: 60〜90分（初回、GCP 初心者基準）
**前提**: GCP アカウント、gcloud CLI、リポジトリ管理権限（GitHub Secrets/Variables 操作可）

---

## 0. ゴール

- `asia-northeast1` リージョンで FastAPI サービス `sns-calendar-api` が稼働
- `min-instances=0`（Scale-to-zero、アイドル時固定費 0円）
- GitHub Actions からパスワードレス認証でデプロイできる（Workload Identity Federation）
- Secret Manager に機密環境変数が登録され、Cloud Run から参照される
- `/health` / `/internal/publish/flush`（X-Internal-Token 認証）が HTTPS で応答する

---

## 1. gcloud CLI インストール＆ログイン

### 1-1. インストール（macOS）

```bash
brew install --cask google-cloud-sdk
gcloud version
```

### 1-2. ログイン

```bash
gcloud auth login                 # ブラウザで認証
gcloud auth application-default login  # ADC（ローカルテスト用）
```

---

## 2. GCP プロジェクト作成

### 2-1. プロジェクト ID を決める

```bash
export GCP_PROJECT_ID="shc-sns-calendar"   # 全世界でユニーク。命名規則: 小文字/数字/ハイフン、6〜30文字
```

### 2-2. プロジェクト作成

```bash
gcloud projects create "$GCP_PROJECT_ID" --name="SHC SNS Calendar"
gcloud config set project "$GCP_PROJECT_ID"
```

### 2-3. 請求先アカウント紐付け（**必須**、無料枠でも必要）

GCP Console で **Billing → Link a billing account**。
無料枠（$300 初回クレジット or Always Free）内なら課金 0 円。

```bash
# CLI の場合（請求先 ID を事前に取得）
gcloud billing accounts list
gcloud billing projects link "$GCP_PROJECT_ID" --billing-account=<BILLING_ACCOUNT_ID>
```

### 2-4. プロジェクト番号の控え

```bash
export GCP_PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')
echo "GCP_PROJECT_NUMBER=$GCP_PROJECT_NUMBER"
```

**重要**: `GCP_PROJECT_NUMBER` は Workload Identity Federation で使う。メモしておく。

---

## 3. 必要な API を有効化

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com
```

有効化まで 1〜2 分かかる。

---

## 4. Artifact Registry リポジトリ作成

Docker イメージの置き場。Container Registry は非推奨（deprecated）なので Artifact Registry を使う。

```bash
export REGION="asia-northeast1"
export REPO="sns-calendar-api"

gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="FastAPI images for SNS Calendar"
```

確認:
```bash
gcloud artifacts repositories list --location="$REGION"
```

---

## 5. Secret Manager にシークレット登録

### 5-1. 登録対象

| Secret 名 | 値のソース |
|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API → service_role key |
| `SUPABASE_ANON_KEY` | 同上、anon key（publicなので env_vars で渡すのも可） |
| `INTERNAL_API_TOKEN` | `openssl rand -hex 32` で生成 |
| `X_CONSUMER_KEY` / `X_CONSUMER_SECRET` | Developer Portal (https://developer.x.com/) |
| `META_APP_ID` / `META_APP_SECRET` | Meta for Developers Dashboard |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | Cloudflare R2 API Token |

### 5-2. 登録コマンド例（stdin 経由で履歴に残さない）

```bash
# 例: SUPABASE_SERVICE_ROLE_KEY
printf '%s' "eyJhbGciOi..." | gcloud secrets create SUPABASE_SERVICE_ROLE_KEY \
  --data-file=- \
  --replication-policy="automatic"

# 例: INTERNAL_API_TOKEN 生成＋登録
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create INTERNAL_API_TOKEN \
  --data-file=- \
  --replication-policy="automatic"
```

すでに存在する場合は `versions add`:

```bash
printf '%s' "newvalue" | gcloud secrets versions add SUPABASE_SERVICE_ROLE_KEY --data-file=-
```

### 5-3. 一覧確認

```bash
gcloud secrets list
```

---

## 6. Service Account 作成（Cloud Run ランタイム用＋GitHub デプロイ用）

### 6-1. ランタイム用 Service Account

Cloud Run 実行中に Secret Manager から値を取得するための権限を持つアカウント。

```bash
gcloud iam service-accounts create cloud-run-runtime \
  --display-name="Cloud Run Runtime Service Account"

export RUNTIME_SA="cloud-run-runtime@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# Secret Manager 読み取り権限
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

### 6-2. GitHub Actions デプロイ用 Service Account

```bash
gcloud iam service-accounts create github-deployer \
  --display-name="GitHub Actions Deployer"

export DEPLOYER_SA="github-deployer@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run デプロイ権限
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/run.admin"

# Artifact Registry 書き込み権限
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/artifactregistry.writer"

# Runtime SA を代理する権限（deploy 時に --service-account を指定するため）
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/iam.serviceAccountUser"
```

---

## 7. Workload Identity Federation（GitHub OIDC → GCP）

Service Account Key（JSON）を使わず、GitHub の OIDC トークンで GCP 認証する方式。Key 流出リスクなし。

### 7-1. Workload Identity Pool 作成

```bash
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"
```

### 7-2. OIDC Provider 登録（GitHub 専用の issuer と attribute mapping）

```bash
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-condition="attribute.repository_owner == 'anorthernsoul0227business'"
```

`--attribute-condition` で **自組織のリポジトリのみ** 認証許可する（他者のfork からの不正 deploy を防ぐ）。

### 7-3. GitHub リポジトリを Service Account に紐付け

```bash
export REPO_FULL="anorthernsoul0227business/joyfoundation-sns-project"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO_FULL}"
```

### 7-4. 登録値のメモ（GitHub Secrets に登録する）

```bash
export GCP_WORKLOAD_IDENTITY_PROVIDER="projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER=$GCP_WORKLOAD_IDENTITY_PROVIDER"
echo "GCP_SERVICE_ACCOUNT=$DEPLOYER_SA"
echo "GCP_PROJECT_ID=$GCP_PROJECT_ID"
```

---

## 8. GitHub Secrets / Variables 登録

### 8-1. Secrets

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project

printf '%s' "$GCP_PROJECT_ID"                      | gh secret set GCP_PROJECT_ID
printf '%s' "$GCP_WORKLOAD_IDENTITY_PROVIDER"      | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER
printf '%s' "$DEPLOYER_SA"                         | gh secret set GCP_SERVICE_ACCOUNT

# INTERNAL_API_TOKEN は Secret Manager に登録済みなので GH 側にも同じ値を登録
#   - GH Actions Cron の publish_flush.yml が curl で使う
gcloud secrets versions access latest --secret=INTERNAL_API_TOKEN \
  | gh secret set INTERNAL_API_TOKEN

# Cloud Run デプロイ後に追加する（本日時点では未デプロイなので後）:
#   CLOUD_RUN_API_URL
```

### 8-2. Variables

```bash
gh variable set CLOUD_RUN_ENABLED --body "true"
# publish_flush は Cloud Run URL 確定後に有効化するのが安全
gh variable set PUBLISH_FLUSH_ENABLED --body "false"
```

### 8-3. 既存の環境変数（参考）

| Secret 名 | 既存? | 用途 |
|---|---|---|
| `SUPABASE_URL` | ✅ | Cloud Run env_vars |
| `SUPABASE_ANON_KEY` | ✅ | Cloud Run env_vars |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Cloud Run Secret Manager |
| `FRONTEND_URL` | ❌ | Vercel の URL（Vercel 構築後に追加） |
| `R2_*` | ✅ | Cloud Run env_vars / Secret Manager |

---

## 9. 初回デプロイ（手動 → 自動）

### 9-1. 手動 build & push で疎通確認（推奨）

GitHub Actions に任せる前に、ローカルから一度デプロイを通しておくと、権限エラーの切り分けが容易。

```bash
cd sns-calendar-app/apps/api

# Artifact Registry に docker 認証
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# M1/M2 Mac は --platform=linux/amd64 必須
docker build --platform=linux/amd64 \
  -t "${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/api:manual-0" .
docker push "${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/api:manual-0"

# Cloud Run デプロイ
gcloud run deploy sns-calendar-api \
  --image "${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/api:manual-0" \
  --region "$REGION" \
  --platform managed \
  --service-account "$RUNTIME_SA" \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=60s \
  --set-env-vars="APP_NAME=SNS Calendar API,ENVIRONMENT=production,SUPABASE_URL=<value>,SUPABASE_ANON_KEY=<value>,R2_ACCOUNT_ID=<value>,R2_BUCKET_NAME=<value>,R2_PUBLIC_URL=<value>" \
  --set-secrets="SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,INTERNAL_API_TOKEN=INTERNAL_API_TOKEN:latest,X_CONSUMER_KEY=X_CONSUMER_KEY:latest,X_CONSUMER_SECRET=X_CONSUMER_SECRET:latest,META_APP_ID=META_APP_ID:latest,META_APP_SECRET=META_APP_SECRET:latest,R2_ACCESS_KEY_ID=R2_ACCESS_KEY_ID:latest,R2_SECRET_ACCESS_KEY=R2_SECRET_ACCESS_KEY:latest"
```

### 9-2. URL 取得＆検証

```bash
export CLOUD_RUN_URL=$(gcloud run services describe sns-calendar-api --region "$REGION" --format='value(status.url)')
echo "$CLOUD_RUN_URL"

# /health 応答確認
curl -sS "${CLOUD_RUN_URL}/health" | jq

# internal endpoint 認証確認（401 期待）
curl -sS -X POST "${CLOUD_RUN_URL}/internal/publish/flush" -w "\nHTTP %{http_code}\n"

# トークン付き（200 + 空 queue なら processed=0）
TOKEN=$(gcloud secrets versions access latest --secret=INTERNAL_API_TOKEN)
curl -sS -X POST "${CLOUD_RUN_URL}/internal/publish/flush" \
  -H "X-Internal-Token: $TOKEN" | jq
```

### 9-3. GitHub Secrets に URL 登録

```bash
printf '%s' "$CLOUD_RUN_URL" | gh secret set CLOUD_RUN_API_URL
gh variable set PUBLISH_FLUSH_ENABLED --body "true"
```

### 9-4. 以降は GitHub Actions で自動デプロイ

`main` ブランチへの push で `.github/workflows/deploy-backend.yml` が発火し、新しいイメージをビルド・デプロイする。

---

## 10. 動作確認チェックリスト

- [ ] `gcloud run services list` に `sns-calendar-api` がある
- [ ] `curl ${CLOUD_RUN_URL}/health` → 200 `{"status":"ok", ...}`
- [ ] `curl ${CLOUD_RUN_URL}/internal/publish/flush` → 401
- [ ] `curl -H "X-Internal-Token: $TOKEN" ${CLOUD_RUN_URL}/internal/publish/flush` → 200
- [ ] GitHub Actions `publish_flush.yml` を手動トリガー → 成功ログ
- [ ] Cloud Run Logs（Console）に FastAPI 起動ログが出る
- [ ] アイドル 15 分後に再リクエスト → コールドスタート 1〜3秒

---

## 11. トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `deploy-backend.yml` が `skipping` | `CLOUD_RUN_ENABLED != 'true'` | `gh variable set CLOUD_RUN_ENABLED --body "true"` |
| `Permission 'iam.serviceAccounts.getAccessToken' denied` | WIF の binding 不足 | Step 7-3 を再実行 |
| `PERMISSION_DENIED: gcloud.auth.login` | デプロイ SA に `roles/run.admin` なし | Step 6-2 で付与 |
| `failed to create secret: already exists` | Secret 既存 | `gcloud secrets versions add ...` で上書き |
| `exec /usr/local/bin/uvicorn: exec format error` | M1/M2 Mac で `--platform=linux/amd64` 未指定 | Dockerfile FROM の下に指定 or build 時に追加 |
| コールドスタートが遅すぎる | scale-to-zero | `--min-instances=1`（$5〜/月 相当の課金発生） |
| `INTERNAL_API_TOKEN is not configured on server` | Cloud Run 側に Secret 紐付け忘れ | `--set-secrets` に `INTERNAL_API_TOKEN=INTERNAL_API_TOKEN:latest` を追加して再デプロイ |

---

## 12. 後片付け（プロジェクトを捨てる場合）

無料枠内でも、プロジェクトを作った事実は残る。不要なら:

```bash
gcloud projects delete "$GCP_PROJECT_ID"
```

削除後 30 日間は復活可能。

---

## 13. 無料枠の目安（2026年4月時点）

| サービス | 無料枠 | 想定使用量 |
|---|---|---|
| Cloud Run リクエスト | 200万/月 | 1日 1000req → 月 3万（余裕） |
| Cloud Run vCPU 秒 | 36万/月 | コールドスタート込み月 5000秒想定（余裕） |
| Cloud Run メモリ | 18万 GiB-秒/月 | 512MiB × 5000秒 = 2500 GiB-秒（余裕） |
| Artifact Registry | 0.5 GB 無料 | イメージ 200MB × 5 世代 = 1GB（超過 $0.10/GB/月） |
| Secret Manager | 6 versions/月 active 無料 | 8 secrets × 1 version = 8 active（超過 $0.06/1万 access） |

**合計月額**: 初期は $0。Artifact Registry で $0.05〜0.10/月、Secret Manager で $0.01/月程度。ほぼ無視できる。

---

## 14. 参考リンク

- Cloud Run 公式: https://cloud.google.com/run/docs
- Workload Identity Federation: https://cloud.google.com/iam/docs/workload-identity-federation
- google-github-actions/auth: https://github.com/google-github-actions/auth
- D 案 設計書: `design/design/APP_DESIGN_SPEC.md` Section 15
