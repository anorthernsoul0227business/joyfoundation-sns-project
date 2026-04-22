# 本番ローンチ チェックリスト（D案 完全無料スタック）

**目的**: 圭一郎さんが `https://shc-sns-calendar.example.com` にアクセスしてSNS管理できる状態にする。
**前提設計**: `design/design/APP_DESIGN_SPEC.md` Section 15（D案 無料スタック移行計画）

---

## Phase A — 基盤構築（開発者作業）

### A-1. Supabase
- [x] プロジェクト作成（`msghvqclexpvgkrctxug`, Tokyo, Free tier）
- [x] マイグレーション 8 本適用
- [x] `notifications` を `supabase_realtime` publication に追加
- [x] `publish_queue` + pg_cron ジョブ登録
- [ ] Auth Settings → Site URL / Redirect URLs に Vercel URL 登録（Vercel デプロイ後）
- [ ] Auth Email Templates の `{{ .SiteURL }}` 参照が正しいか確認

### A-2. GCP Cloud Run
詳細は `docs/ops/cloud_run_setup.md`。
- [ ] プロジェクト作成＆請求先紐付け
- [ ] API 有効化（run / artifactregistry / secretmanager / iamcredentials）
- [ ] Artifact Registry `sns-calendar-api` 作成
- [ ] Secret Manager に 8 シークレット登録
- [ ] Runtime SA + Deployer SA 作成＋ IAM Binding
- [ ] Workload Identity Federation 設定
- [ ] 手動 docker build & deploy で `/health` 応答確認
- [ ] GitHub Secrets: GCP_PROJECT_ID / GCP_WORKLOAD_IDENTITY_PROVIDER / GCP_SERVICE_ACCOUNT / INTERNAL_API_TOKEN / CLOUD_RUN_API_URL
- [ ] GitHub Variables: `CLOUD_RUN_ENABLED=true` / `PUBLISH_FLUSH_ENABLED=true`
- [ ] `main` への push で `deploy-backend.yml` が成功

### A-3. Vercel
詳細は `docs/ops/vercel_setup.md`。
- [ ] プロジェクト作成（Root Directory: `sns-calendar-app/apps/web`）
- [ ] 環境変数登録（NEXT_PUBLIC_API_BASE_URL / SUPABASE_URL / SUPABASE_ANON_KEY）
- [ ] 初回デプロイ成功、URL 発行
- [ ] Cloud Run 側 `FRONTEND_URL` を Vercel URL に更新 → 再デプロイ

### A-4. GitHub Actions Cron
- [ ] `publish_flush.yml` を手動トリガーして成功を確認
- [ ] 5分後の自動実行がログに残る

---

## Phase B — 機能動作確認（開発者作業）

### B-1. 認証
- [ ] `/signup` で新規アカウント作成
- [ ] メール認証（Supabase Auth のメール） or Resend 経由
- [ ] `/login` で再ログイン
- [ ] セッション永続化確認（リロードしてもログイン状態）

### B-2. 投稿作成
- [ ] `/create` で下書き作成（X/IG 両方）
- [ ] 画像アップロード（R2 に保存される）
- [ ] `/drafts` で下書き一覧表示
- [ ] 下書きを編集・複製・削除
- [ ] プレビューパネル（X/IG 実サイズ）

### B-3. 予約投稿
- [ ] 下書きを予約時刻付きで保存
- [ ] `/calendar` で予約が表示される
- [ ] サイドバー → カレンダーの D&D で時刻変更
- [ ] 予約時刻到達 → 1分以内に `publish_queue` に enqueue（pg_cron）
- [ ] 5分以内に GH Actions が `/internal/publish/flush` を叩く
- [ ] X/IG 両方で実投稿成功
- [ ] `notifications` テーブルに INSERT → ブラウザに Realtime 通知

### B-4. SNS アカウント連携
- [ ] `/settings/sns` で X OAuth 認証
- [ ] `/settings/sns` で IG Business OAuth 認証
- [ ] トークン保存・有効期限管理

### B-5. 通知
- [ ] ヘッダーベルに未読カウント
- [ ] `/notifications` で履歴表示
- [ ] 既読処理（個別・全件）
- [ ] 新着通知が Realtime で即反映

---

## Phase C — 圭一郎さん オンボーディング

### C-1. アカウント作成
- [ ] 圭一郎さんのメールアドレスで `/signup`
- [ ] 初期パスワードを設定（パスワードマネージャに記録）
- [ ] 組織（Organization）作成 → 圭一郎さんを `admin` 役で登録

### C-2. SNS 連携
- [ ] 圭一郎さんの Facebook ID で Meta OAuth 認証
- [ ] IG Business アカウントの選択確認
- [ ] X アカウント（@SFH_Science）で X OAuth 認証

### C-3. 投稿テスト
- [ ] テスト投稿（非公開 or test アカウント）を予約
- [ ] 予約時刻に自動投稿されることを確認
- [ ] 圭一郎さんのメールに結果通知が届く

### C-4. 使い方ガイド
- [ ] シンプルモード（`ui_mode=simple`）が有効
- [ ] ヘルプモード（?アイコン）が有効
- [ ] 初回ログイン時のツアー（ARCH-005/Resend 完了後に検討）

### C-5. 移行（必要に応じて）
- [ ] 既存の Google Sheets 予約投稿を段階的に Web UI へ移行
- [ ] 自動投稿システム（launchd + GH Actions auto_post.yml）との併用期間を決める

---

## Phase D — 販売化準備（将来）

- [ ] Vercel Pro 契約（商用利用）
- [ ] Supabase Pro（PITR バックアップ、MAU 50K 超過対応）
- [ ] 独自ドメイン取得・DNS 設定
- [ ] Resend Pro（認証メール・通知メール）
- [ ] 料金体系決定（Freemium / Per-seat / Per-org）
- [ ] プライバシーポリシー / 利用規約作成
- [ ] Stripe / Square 連携（決済）
- [ ] サポート窓口整備（ヘルプセンター、問い合わせフォーム）

---

## 関連ドキュメント

- 設計: `design/design/APP_DESIGN_SPEC.md` Section 15
- GCP 手順: `docs/ops/cloud_run_setup.md`
- Vercel 手順: `docs/ops/vercel_setup.md`
- ARCH-001〜005 ブリーフィング: `docs/codex_brief_ARCH-00[1-5].md`
