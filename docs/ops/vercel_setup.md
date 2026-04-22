# Vercel セットアップ手順書（Frontend 本番デプロイ）

**対象**: `sns-calendar-app/apps/web` の Vercel デプロイ
**想定所要時間**: 20〜30分
**前提**: Vercel アカウント、GitHub リポジトリ管理権限、Cloud Run API URL 確定済み

---

## 0. ゴール

- Vercel Hobby プラン（無料）で Next.js 15 + React 19 アプリが稼働
- `main` への push で自動デプロイ
- 環境変数（Supabase / API URL）が設定済み
- `https://<vercel-domain>.vercel.app` でログイン画面が開く

---

## 1. Vercel アカウント準備

### 1-1. サインアップ

https://vercel.com/signup → GitHub 連携でサインアップ（権限: `read:org` / `repo` は後で Import 時に要求される）。

### 1-2. Hobby プランの商用利用可否確認

Vercel Terms of Service により **Hobby プランは non-commercial 利用限定**。SaaS として販売する段階では Pro ($20/月) 必須の可能性が高い。
- 圭一郎さん個人利用・NPO 広報ツールの段階では Hobby 利用可の解釈が可能
- 商用化判断時に再レビュー（`tasks.md` #12 Supabase 運用検討の派生として管理）

---

## 2. プロジェクトの Import

### 2-1. Dashboard から Import

1. Vercel Dashboard → **Add New... → Project**
2. GitHub リポジトリ `joyfoundation-sns-project` を選択
3. **Import**

### 2-2. プロジェクト設定

| 項目 | 値 |
|---|---|
| Project Name | `shc-sns-calendar-web` |
| Framework Preset | Next.js |
| Root Directory | **`sns-calendar-app/apps/web`**（重要） |
| Build Command | `cd ../.. && pnpm build` |
| Output Directory | `.next`（デフォルト） |
| Install Command | `cd ../.. && pnpm install --frozen-lockfile` |
| Node.js Version | 20.x |

**モノレポ注意**: Root Directory を `apps/web` にしても、pnpm workspace の依存を解決するため Build/Install コマンドは親ディレクトリから実行する必要がある。

### 2-3. 初回 Import 前に環境変数を追加（推奨）

| Key | Value | Environment |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Cloud Run URL（例: `https://sns-calendar-api-xxx.run.app`） | Production / Preview |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://msghvqclexpvgkrctxug.supabase.co` | Production / Preview |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | Production / Preview |

### 2-4. Deploy

「Deploy」押下 → 2〜3分でビルド完了。URL が発行される（例: `https://shc-sns-calendar-web.vercel.app`）。

---

## 3. Cloud Run 側の CORS / 環境変数更新

Vercel URL が確定したら、Cloud Run 側にも反映する必要がある:

### 3-1. FRONTEND_URL を GitHub Secrets に追加

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project
export VERCEL_URL="https://shc-sns-calendar-web.vercel.app"

printf '%s' "$VERCEL_URL" | gh secret set FRONTEND_URL
```

### 3-2. Cloud Run 再デプロイ

`main` ブランチに empty commit を push するか、GitHub Actions `deploy-backend.yml` を手動トリガー。

Cloud Run の `--set-env-vars` に `FRONTEND_URL=${VERCEL_URL}` が注入され、FastAPI 側の `allowed_origins` に加わる。

---

## 4. 動作確認

### 4-1. 画面アクセス

```
https://shc-sns-calendar-web.vercel.app/login
```

### 4-2. サインアップ → ログイン → ホーム画面

1. `/signup` で新規アカウント作成
2. `/login` でログイン
3. ホーム画面（`/`）が表示される
4. DevTools の Network タブで `NEXT_PUBLIC_API_BASE_URL` 先（Cloud Run）への POST が通っていることを確認
5. `/notifications` を開いて、Supabase Realtime の WebSocket 接続が張られることを確認

### 4-3. 失敗パターン（トラブルシューティング）

| 症状 | 原因 | 対処 |
|---|---|---|
| `Failed to fetch` on login | Cloud Run 側 CORS が Vercel URL を含まない | Step 3 で FRONTEND_URL 更新 |
| Supabase Realtime 接続失敗 | anon key 不正 / Project URL 不正 | Vercel 環境変数を再確認 |
| Build fail: `Cannot find module '@supabase/supabase-js'` | Root Directory 設定ミス | `sns-calendar-app/apps/web` に合わせる |
| Build fail: `ELIFECYCLE pnpm install` | Node version / pnpm version | Project Settings → Node.js Version を 20.x |

---

## 5. カスタムドメイン（任意）

Vercel Dashboard → Project → Settings → Domains から追加:

1. `shc-sns-calendar.your-domain.com` を追加
2. DNS レコード（CNAME or A）を指定の値に設定
3. SSL 自動発行（Let's Encrypt）

Resend（ARCH-005）で同じドメインから送信メールを出すなら、親ドメインを取得しておくと便利。

---

## 6. Preview Deployments

`main` 以外のブランチに push すると、Vercel が自動で Preview URL を発行する（PR にもコメントで通知）。

- 本番環境変数（`NEXT_PUBLIC_*`）は Production / Preview 両方にチェック入れておくこと
- Preview と Production で別 Cloud Run を使いたい場合は、環境変数を Environment別に切り替え

---

## 7. コスト見積もり

Vercel Hobby 無料枠:
- 帯域 100 GB/月
- ビルド 6,000分/月
- Serverless Functions 実行 100 GB-Hour/月
- Team Member 1 人

圭一郎さん + 康二郎さん個人利用なら、無料枠内で十分。

Pro ($20/月) への昇格トリガー:
- Team 2 名以上
- 帯域 100 GB 超過
- **商用利用**（販売開始時）

---

## 8. 参考リンク

- Vercel Monorepo (Turborepo): https://vercel.com/docs/monorepos/turborepo
- Vercel 環境変数: https://vercel.com/docs/projects/environment-variables
- D 案 設計書: `design/design/APP_DESIGN_SPEC.md` Section 15
