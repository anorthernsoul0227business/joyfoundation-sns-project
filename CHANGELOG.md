# Changelog

プロジェクト全体のリリースノート。Phase 1 MVP 以降を記録する。

## [0.1.0] - 2026-04-22 (Phase 1 MVP)

初リリース。サウンドヒーリング協会／ジョイファンデーション向け SNS 投稿管理アプリの最小機能版。

### 認証・アカウント
- メール / パスワードによるサインアップ・ログイン (Supabase Auth + JWT + JWKS)
- ユーザープロファイル（表示名・UI モード・ヘルプモード）
- X OAuth 1.0a / Instagram OAuth 2.0 での SNS アカウント連携
- `/settings/sns` で接続状態の閲覧と切断

### 投稿
- `/create` での投稿作成（X / Instagram 両対応）
- 下書き保存 (`/drafts`)
- 予約投稿（Celery beat + worker）
- 即時投稿 (`publish-now`)
- IG カルーセル (2〜10 枚画像)
- X / IG API 実投稿 Publisher 実装

### カレンダー
- FullCalendar ベースの月次ビュー (`/calendar`)
- 下書き D&D → カレンダー配置 (予約化)
- プラットフォームフィルタ

### 通知
- SMTP_SSL による投稿結果メール通知
- WebSocket (`/ws/notifications`) リアルタイム通知
- ベルアイコン未読カウント
- 通知履歴ページ (`/notifications`)
- 既読 / 全件既読

### 画像
- `POST /api/media/upload`
- Cloudflare R2 への保存
- `auto_resize_ig=true` で 4:5 (1080x1350) 白余白パディング
- 画像上限 10MB / リクエスト 10 枚

### ホーム画面
- シンプルモード (`/`)
- 今日・明日の投稿予定
- 最近の下書き（横スクロール）
- SNS 未接続時の警告バナー

### インフラ
- Supabase Cloud (Postgres + RLS + Auth)
- Railway (FastAPI / Celery worker / Celery beat / Redis)
- Vercel (Next.js フロント)
- Cloudflare R2 (画像ストレージ)

### CI/CD
- `.github/workflows/ci.yml` — typecheck / build / lint / pytest / OpenAPI schema sync / axios サプライチェーン監査
- `.github/workflows/deploy-frontend.yml` — Vercel デプロイ（opt-in）
- `.github/workflows/deploy-backend.yml` — Railway デプロイ（opt-in）
- `.github/workflows/e2e.yml` — Playwright E2E（opt-in）

### テスト
- pytest (バックエンド): 87 passed / 44 skipped
- Playwright E2E 骨格 (apps/web/tests/e2e/): core-flow / auth / drafts / calendar / settings-sns / notifications

### ドキュメント
- [`docs/OPS_RUNBOOK.md`](docs/OPS_RUNBOOK.md)
- [`docs/GO_LIVE_CHECKLIST.md`](docs/GO_LIVE_CHECKLIST.md)
- [`docs/KPI.md`](docs/KPI.md)
- [`docs/ENV_VARS.md`](docs/ENV_VARS.md)

### 並走運用
- 既存 `sns-auto-poster/` (launchd) と 2 週間並走
- Google Sheets に `Webアプリ化済` フラグを追加し重複投稿を防ぐ

---

### 対象外（Phase 2 以降）
- Note / YouTube / LINE 対応
- リール / 動画投稿
- AI 投稿生成
- 外部ユーザー向けリリース
- 料金プラン / 課金
- 視覚的回帰テスト・APM (Sentry 等)
- モバイルブラウザ・ネイティブアプリ対応
