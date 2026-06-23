# 開発ログ (DEVLOG)

## 2026-06-23

### 実施内容
- 未コミット作業の整理（Work A コミット / 死蔵 Celery scaffold 削除）を PR #30 でマージ
- 康二郎さん本番初使用フィードバック4件のうち、即効性の高い2件を実装:
  1. **画像ドラッグ&ドロップアップロード**（`apps/web/src/app/create/page.tsx`）:
     - 画像リスト領域を drop ゾーン化。ドラッグ中はアウトライン+空状態テキストでハイライト
     - drop された画像ファイル（JPEG/PNG/WebP）のみ抽出し既存 `handleMediaUpload` で R2 アップロード
     - dragenter/leave の深さカウントで子要素跨ぎのちらつきを防止、非画像 drop はエラー表示
  2. **ヘルプ吹き出しの画面端見切れ修正**（`apps/web/src/components/HelpMark.tsx`）:
     - 依存追加なしで、アンカー位置とポップオーバー実寸からビューポート端を検知
     - 水平オフセット補正 + 下端で見切れる場合は上方向にフリップ、resize/scroll で再計算

### 成果
- web typecheck 通過。実ユーザー要望の UX 改善2件を MVP に追加

### 課題・備考
- 残2件（Googleドライブ連携 / RAG ナレッジ積み上げ）は設計・外部API設定を要する大物として別途
- D&D とツールチップ位置は実機でのインタラクション確認が望ましい

### 追加実装（同日）: Google Drive 画像ピッカー（要望②）
- **方式決定**: サービスアカウント方式（既存 Sheets 用 SA を再利用）＋ 選択画像は R2 にコピー（publisher が http URL 前提のため整合）。Picker/個別OAuth は使わずシニア配慮でログイン不要に
- **バックエンド**:
  - `app/services/drive.py`: SA で共有フォルダの画像/サブフォルダ一覧・DL・サムネ取得（thumbnailLink 優先でグリッド高速化）。重い google-api-python-client は使わず google-auth + Drive REST
  - `app/api/drive.py`（`/api/media/drive/*`）: `GET /list`・`GET /thumbnail/{id}`・`POST /import`（DL→既存 upload_original→public_url 返却）
  - config に `GOOGLE_SERVICE_ACCOUNT_JSON/_FILE`・`DRIVE_SHARED_FOLDER_ID` 追加。依存 `google-auth` 追加
  - テスト: 単体7＋API7（Drive はフェイク、R2 は moto）= 全通過
- **フロント**:
  - `components/DriveImagePicker.tsx`: フォルダ階層ナビ＋画像グリッドのモーダル。サムネは認証付き fetch→blob で表示、選択→import→media 配列へ append
  - api-client に `listDriveImages`/`importDriveImage`/`fetchDriveThumbnailBlob`、生成 SDK 再生成
  - create ページに「Drive から選ぶ」ボタン追加
- **検証**: web typecheck / backend pytest（97 passed）/ ruff 通過
- **実 Drive スモークテスト**: 既存 SA で実機検証。Drive API は既に有効、`HSC_SNS用画像フォルダ`(`1vPODCZ9...`)が SA に共有済みと判明（旧 ID `1TbaQla9...` は未共有）。list/download/thumbnail すべて実 HTTP で成功
- **残ops**: 本番のみ Cloud Run に SA資格情報 Secret＋`DRIVE_SHARED_FOLDER_ID=1vPODCZ9...`（gcloud 環境が必要）

### 本番デプロイ（フロント, 同日）
- 第1ゴール=「圭一郎さんが使える状態」を確認（速度優先・急造可だが変更容易性は維持）。投稿公開は当面レビュー/手動ゲート（=方式B）、将来の完全自動投稿(A)はその延長線
- デプロイ機構を確認: フロントは **Vercel CLI 手動**（GH Actions deploy は無効）。本番は #29(ef094be) で止まっていた
- ローカルが Node 25 で `next dev` がハングするが、**Vercel リモートビルド(Node 20)** でプレビュー→本番昇格。#30(実画像プレビュー)・#31(D&D/ヘルプ)・#32(Drive UI) を本番反映
- ブラウザで本番描画＋HelpMark ツールチップ表示を確認。Drive ボタンはバックエンド(Cloud Run)未更新のため一時休眠

---

## 2026-04-23

### 実施内容
- **4/22 自動投稿稼働実績の確認**:
  - 12:00 配信の3件すべて成功（Gmail通知で確認）
    - X「仙台スターライト あと3日」
    - X「カンガルーカップ 協賛告知」
    - IG「日本人だけ？虫の声を聴く感性」
- **圭一郎さんからの 4/21 返信対応**:
  1. **カンガルーカップ日付修正（4/28-30 → 4/28-5/3）**:
     - 全シートを点検し、投稿テキストはほぼ全て既に `4/28-5/3 決勝5/3` で正しい状態と判明
     - 唯一 Xイベント投稿 Row 15「4月まとめ」マスタの `4/27-5/3` を `4/28-5/3` に修正（告知対象外だが整合性確保）
  2. **ファシリテーター研修 第89期（6/12-14）告知の複数回スケジュール**:
     - X 4本 + IG 3本を投稿キューに投入
     - 5/1(金) GW初回告知 / 5/15(木) 1ヶ月前 / 5/29(金) 2週間前 / 6/9(火) 直前リマインド（X のみ）
     - 各回でアングル変更（GW検討 → 残期間カウントダウン → 直前案内）
     - NG表現（効果断言等）回避、画像はマスタの研修会写真を流用

### 成果
- 自動投稿システムが本番安定稼働中（4/22 12:00 配信3/3件成功）
- 圭一郎さん依頼2件完了、6/12開催の認定研修への早期申込導線を確保

### 課題・備考
- 6月投稿分の写真について圭一郎さんが一部差し替え予定（連絡待ち）
- 89期 X #4（6/9 直前）の文面は実際の残席状況確認後、必要に応じて更新可能性あり

---

## 2026-04-22

### 実施内容
- 圭一郎さん向けサポート方針検討（ゼンさんproject側で相談 → joyfoundation に反映）
- ゼンさんPDF「エージェントワークの運用構成と役割分担」を確認し、git ベース非同期エージェント連携の構成を把握
- 圭一郎さん（高齢・PC操作困難）向けサポートアーキテクチャを検討し、以下を決定:
  - **SNS投稿支援**: 既存Webアプリに音声入力AIを統合する方向（音声レイヤ追加のみで完結、PCエージェント常駐は避ける）
  - **PC遠隔エージェント層**: 保留。Webアプリ完成後に再検討
- `APP_DESIGN_SPEC.md` に **Section 14「音声入力AI増分設計 v0.1」** を追加:
  - F-28〜F-32（マイクボタン / リアルタイム音声ブレスト / 対話指示 / TTS確認 / 固有名詞辞書）
  - 技術選定: Whisper API を暫定採用（未決定事項の暫定解消）、`packages/voice-provider/` でプロバイダ抽象化
  - 新規API: `/api/voice/transcribe`, `/api/voice/brainstorm`, `/api/voice/refine`, `/api/voice/vocabulary`, `/api/voice/sessions`
  - 新規モデル: VoiceVocabulary, VoiceSession（90日自動削除）
  - UI設計: シンプルモードに画面下部固定マイクボタン、音声ブレストモーダル、TTS送信前確認モーダル
  - Phase 1.5 組み込み方針、+2〜3週の実装見積もり、VOICE-001〜007 の Issue 案
- 既存設計との整合を確認:
  - F-16（バッチ型音声→投稿）とは実装基盤を共有
  - 決定#6（AI API 両対応）、決定#11-12（org_id RLS）、決定#15（NG 3層チェック）、決定#26-27（シニア配慮ヘルプ）と整合
  - 未決定「音声文字起こし Whisper vs Google STT」を暫定決定としてクロスリファレンス追記

### 成果
- 音声入力機能の増分設計書（Section 14）完成、MVP から Phase 1.5 で組み込む計画に
- 別プロジェクト化の判断回避（feature branch 戦略で Turborepo モノレポの恩恵を維持）

### 課題・備考
- **圭一郎さんの音声サンプルでの Whisper 精度実測**がブロッカー。`scripts/voice-poc/whisper_precision_test.py` を次タスクとして作成予定
- iOS Safari のマイク権限 UX は実機検証が必要
- TTSエンジン（ブラウザ SpeechSynthesis vs OpenAI TTS）の選定は未決
- 本設計は `main` ブランチ上の追記（計画ドキュメントのため）。実装着手時に `feat/voice-input` を切る

---

## 2026-04-22（夜・GCP + Vercel 本番稼働）

### 実施内容
- **GCP Cloud Run セットアップ**（手順書どおりに実行、所要 約60分）:
  - プロジェクト `shc-sns-calendar`（番号 817894013861）作成＋Billing 紐付け
  - API 有効化: run / artifactregistry / secretmanager / iamcredentials / cloudbuild
  - Artifact Registry `sns-calendar-api`（asia-northeast1）
  - Secret Manager に 9 シークレット登録（Supabase / X / Meta / R2 / INTERNAL_API_TOKEN）
  - Service Account 2種（cloud-run-runtime / github-deployer）
  - Workload Identity Federation（github-pool + github-provider）
  - GitHub Secrets 登録（GCP_*、INTERNAL_API_TOKEN、CLOUD_RUN_API_URL）
  - GitHub Variables 設定（CLOUD_RUN_ENABLED / PUBLISH_FLUSH_ENABLED = true）
- **Cloud Run 初回デプロイ**:
  - 1回目: config.py の `parents[3]` が IndexError で起動失敗
  - fix PR #27 で `_safe_env_file` ヘルパー追加、try/except で None 許容化
  - 2回目: デプロイ成功 → `/health` 200、`/internal/publish/flush` 401/200 確認
- **GH Actions Cron 疎通**: `publish_flush.yml` 手動トリガー → 6秒で success
- **Vercel デプロイ**:
  - Vercel CLI ログイン（GitHub OAuth）
  - プロジェクト `shc-sns-calendar-web` 作成
  - 初回デプロイ失敗（Next.js 未検出） → Vercel API で rootDirectory を `apps/web` に変更
  - 2回目デプロイ成功: https://shc-sns-calendar-web.vercel.app
- **Cloud Run CORS 連動**:
  - `FRONTEND_URL` 環境変数を Vercel URL で更新 → Cloud Run 新リビジョン `sns-calendar-api-00003-dfd`
  - OPTIONS preflight で `access-control-allow-origin: https://shc-sns-calendar-web.vercel.app` を確認

### 成果
- **完全無料スタック**が本番稼働開始（Supabase + Vercel + Cloud Run + R2 全て無料枠内）
- フロント〜バックエンド〜DB〜Realtime〜Cron の5層が疎通
- **固定費 $0/月**で SaaS 販売可能な基盤が完成
- 圭一郎さんがアクセスできる本番URL確定: https://shc-sns-calendar-web.vercel.app

### 残課題
- Supabase Auth Settings → Site URL / Redirect URLs に Vercel URL を登録（ブラウザから認証メールのリダイレクトを成立させるため）
- 圭一郎さんユーザー登録 + SNS OAuth 連携（X / IG Business）
- ARCH-005 Resend（認証メール用 SMTP、現状 Supabase デフォルト SMTP 使用中 = 1日3通制限）
- B2 ファシリ89期告知反映
- Supabase 運用検討（#12）

### 備考
- Vercel プロジェクト設定（rootDirectory / buildCommand / installCommand）は CLI で直接変更できず、Vercel API (`PATCH /v9/projects/{id}`) で更新
- `vercel.json` を monorepo root に置くアプローチは Next.js 検出に失敗、project-level 設定のほうが安定
- Cloud Run の環境変数更新は `gcloud run services update --update-env-vars=` で新リビジョン作成（イメージ再ビルド不要）

---

## 2026-04-22（夕方・D案実装着手：ARCH-001/002/003/004 コード側完了）

### 実施内容
- **ARCH-003 Realtime 移行**:
  - Supabase migration `20260422120000_enable_realtime_notifications.sql` 追加・本番適用
  - `apps/api/app/api/notifications_ws.py` 削除、`main.py` から /ws ルート削除
  - `notifier.py` の `_publish_redis` + redis/json/os 依存削除
  - Web 側に `@supabase/supabase-js` 追加、`apps/web/src/lib/supabase.ts` 新規、`useNotifications.ts` を Realtime 版に書き換え
  - `apps/web/.env.example` に `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` 追加
- **ARCH-001 pg_cron + publish_queue**:
  - Supabase migration `20260422130000_publish_queue_pgcron.sql` 追加（マイグレーションファイルはコミットのみ、本番適用は別途）
  - `apps/api/app/api/internal.py` 新規、`/internal/publish/flush` エンドポイント実装
  - `config.py` に `INTERNAL_API_TOKEN` 設定追加
  - `.github/workflows/publish_flush.yml` 新規（5分毎、`PUBLISH_FLUSH_ENABLED=true` 条件付き）
- **ARCH-002 Celery 撤廃 + Publisher service**:
  - `apps/api/app/services/publish_flush.py` 新規（既存 `scheduled_posts.py` のロジック移植）
  - `apps/api/app/tasks/` ディレクトリ一式削除（celery_app.py / scheduled_posts.py / __init__.py）
  - `tests/tasks/test_scheduled_posts.py` / `tests/test_celery.py` 削除
  - `railway.worker.json` / `railway.beat.json` / `railway.json` 削除
  - `pyproject.toml` から `celery` / `redis` 依存削除（poetry lock 再生成）
  - `apps/api/tests/api/test_internal.py` 新規（token 認証テスト 5件）
- **ARCH-004 Cloud Run デプロイ準備（コード側のみ）**:
  - `.github/workflows/deploy-backend.yml` を Cloud Run 用に書き換え（Workload Identity Federation）
  - `railway.json` 削除
  - 既存 Dockerfile はそのまま利用可（PORT 環境変数対応済み）
  - `/health` エンドポイントも既存（HealthResponse 含む）

### 成果
- **Celery + Redis 依存完全撤廃**。Docker イメージの軽量化（redis/celery/amqp/billiard 等 13パッケージ削除）
- **通知配信が Supabase Realtime に統合**。RLS の SELECT policy が認可境界として機能、サーバー側の JWT 検証・接続管理が不要
- **予約投稿ジョブ基盤が完成**（pg_cron → publish_queue → FastAPI /flush → publisher/orchestrator）
- **Cloud Run デプロイワークフロー**準備完了（GCP 側のプロジェクト・WIF 設定は次タスク）
- テスト: API 78 passed / Frontend typecheck/lint/build すべて成功
- OpenAPI スキーマ更新（`internal` ルート追加、`tests/api/test_internal.py` で検証）

### 残課題
- **pg_cron マイグレーション本番適用**: 動作確認後に `supabase db push` で `20260422130000` を適用
- **GCP セットアップ**（手動）: プロジェクト作成・API 有効化・Artifact Registry 作成・Workload Identity Federation
- **GitHub Secrets 追加**:
  - `INTERNAL_API_TOKEN`（`openssl rand -hex 32` で生成）
  - `CLOUD_RUN_API_URL`（Cloud Run デプロイ後）
  - `GCP_PROJECT_ID` / `GCP_WORKLOAD_IDENTITY_PROVIDER` / `GCP_SERVICE_ACCOUNT`
- **GitHub Variables**:
  - `CLOUD_RUN_ENABLED=true`（deploy-backend 有効化）
  - `PUBLISH_FLUSH_ENABLED=true`（GH Actions cron 有効化）
- **ARCH-005 Resend**: 未着手

### 備考
- 既存 `.github/workflows/auto_post.yml`（CSV シート連携の自動投稿）は別用途なので触らない
- Phase 1 MVP の実装コード（`apps/api/app/services/publisher/`）は流用。Celery を剥がして同期呼び出しに変更しただけ
- ブランチ: `feat/arch-003-realtime-migration`（PR #25）。当初は ARCH-003 単体だったが、時間効率から ARCH-001/002/004 を同じブランチに積んでいる

---

## 2026-04-22（午後・P1→D案方針転換）

### 実施内容
- **P1. Supabase 本番準備 完了**:
  - 既存プロジェクト `sns-calendar-app`（ref: `msghvqclexpvgkrctxug`, Tokyo, Free tier）にリンク
  - マイグレーション6本を本番適用（`supabase db push`）
  - GitHub Secrets に SUPABASE_URL / ANON_KEY / SERVICE_ROLE_KEY 登録
  - `apps/web/.env.example` を新規作成（Web は API 経由のため NEXT_PUBLIC_API_BASE_URL のみ）
- **方針転換**: 圭一郎さん個人利用 → **SaaS 販売化を目標** に変更。固定費ゼロの設計を優先
- **D案「無料スタック移行計画」決定**:
  - 現行 Phase 1 MVP: Railway ($5〜10/月) + Celery + Redis 前提
  - 移行後: Cloud Run (Scale-to-zero) + pg_cron + GitHub Actions Cron + Supabase Realtime
  - 固定費 **月額 0 円**、販売収益と従量課金で連動スケール
- `APP_DESIGN_SPEC.md` に **Section 15「無料スタック移行計画 v0.1」** を追加:
  - 15.1 背景と目的（SaaS販売前提の固定費ゼロ設計）
  - 15.2 現行 vs D案の構成比較（8レイヤ）
  - 15.5 ARCH-001〜005 実装タスク（計 2〜3 日）
  - 15.7 監視と昇格トリガー（7サービス別の警告閾値）
  - 15.8 リスクと緩和策（コールドスタート / 二重化 / 仕様変更）
- **ARCH-001〜005 Codex ブリーフィング作成**:
  - ARCH-001: Celery Beat → pg_cron + GH Actions Cron
  - ARCH-002: Celery Worker → FastAPI 内部エンドポイント
  - ARCH-003: Redis PubSub → Supabase Realtime
  - ARCH-004: Railway → Cloud Run（Workload Identity Federation）
  - ARCH-005: Resend 導入（認証メール・投稿結果通知）

### 成果
- 販売化可能な **固定費ゼロ** アーキテクチャの設計書完成
- 5つの Codex ブリーフィングで実装着手準備完了（工数見積もり 2〜3 日）
- Phase 1 MVP を破棄せず、漸進的に置換する移行戦略（`feat/free-stack-migration` ブランチ）

### 課題・備考
- **Vercel Hobby Free の商用利用規約**確認必要（SaaS 販売で規約違反にならないか）
- **Cloud Run Workload Identity Federation** の初回セットアップ（GCP プロジェクト・IAM・OIDC）
- **独自ドメイン取得**（Resend SPF/DKIM、Cloud Run カスタムドメイン）未決
- **販売モデル**（Freemium / Per-seat / Per-org）は BIZ-001 別設計書で扱う
- 本日は設計フェーズ完了、実装は明日以降。今日は P2 Vercel も着手せず（Cloud Run 先行が合理的）

---

## 2026-04-16（午後）

### 実施内容
- Codex壁打ち R5: Phase 1 実装計画（実装寄り3テーマ）
- 実装計画書作成（`design/design/IMPLEMENTATION_PLAN.md`）:
  - Turborepo + pnpmモノレポ構成（確定版ディレクトリ構造）
  - OpenAPI自動生成パイプライン（FastAPI Pydantic → TypeScript型）
  - インフラ/DevOps設計（Vercel + Railway + Supabase + R2）
  - FullCalendar + dnd-kit統合設計（Phase 1はFC公式Draggableのみに決定）
  - 30 Issue / 4 Sprint / 7-8週間のIssue分割
  - コスト試算（MVP: ~$5-15/月、PMF後: ~$60-80/月）
- Postiz（OSS SNSスケジューラ）のアーキテクチャを参考調査
- APP_DESIGN_SPEC.md に決定事項#20-25を追記
- UIモックアップに下書き一覧ページを追加（全5画面に）

### 成果
- 設計フェーズ完了 → 実装着手可能な状態に
- 設計ドキュメント合計8ファイル完成

### 課題・備考
- 未読メール（4/15 定期スケジュール）の対応が必要
- WS参加費変更（¥2,500→¥3,000）のシート反映が必要
- 音のウエルビーイングOnline 5/19開始が確定
- `sns_accounts.access_token` の at-rest 暗号化は follow-up issue 化が必要（pgcrypto 等を別Issueで導入）

---

## 2026-04-16

### 実施内容
- Codex壁打ち R3: RLS設計レビュー + LLM品質評価基盤
- RLS設計書作成（`design/design/RLS_DESIGN.md`）:
  - 全テーブルのRLSポリシー設計（SQL付き）
  - org_id方式のマルチテナント設計（Phase 2チーム機能への拡張準備）
  - トークン保護設計（sns_accounts_safeビュー）
  - service_role vs ユーザーロールの使い分けマトリクス
  - インデックス戦略（カレンダー表示パフォーマンス99%+改善見込み）
  - pgTapテスト例
- LLM品質評価基盤設計書作成（`design/design/LLM_EVAL_DESIGN.md`）:
  - 6軸品質メトリクス設計（トーン/正確性/エンゲージメント/文字数/NG/自然さ）
  - 3層ハイブリッドNGチェック（ルールベース→辞書→LLM）
  - LLM-as-Judge評価プロンプト設計（バイアス対策込み）
  - 薬機法NGワード辞書設計
  - プロンプトバージョニング + eval_logsテーブル設計
  - ABテスト基盤設計（オフライン/オンライン）
  - コスト試算: 1投稿あたり~$0.032、月60件で~$5.52
- APP_DESIGN_SPEC.md に決定事項#11-17を追記
- Codexブリーフィング作成（`docs/codex_rls_llm_briefing.md`）
- Codex壁打ち R4: note.com連携の法務/規約確認
- note.com規約調査（第22版 2026/1/15制定）:
  - 公式投稿APIは存在しない（公開予定も未定）
  - 非公式APIエンドポイントは405 Not Allowedでブロック済み
  - 利用規約でスパム的活動・技術的措置の回避を禁止
  - 競合ツール（Buffer/Hootsuite/Later）もnote未対応
- note連携設計書作成（`design/design/NOTE_INTEGRATION_DESIGN.md`）:
  - Phase 1: 下書き補助+手動投稿（リスクゼロ）
  - RSS連携で投稿済み自動検知（公式サポート）
  - oEmbed活用の記事プレビュー
  - publisher抽象化でAPI公開時に即応可能な設計
  - note社への事前問い合わせテンプレート作成
- APP_DESIGN_SPEC.md に決定事項#18-19を追記

### 成果
- **優先アクション5件中5件すべて完了**
- 設計ドキュメント合計7ファイル:
  - APP_DESIGN_SPEC.md（更新）
  - CODEX_REVIEW_20260416.md
  - PLATFORM_MATRIX.md
  - RELIABILITY_DESIGN.md
  - RLS_DESIGN.md（新規）
  - LLM_EVAL_DESIGN.md（新規）
  - NOTE_INTEGRATION_DESIGN.md（新規）

### 課題・備考
- 評価データセット構築には既存承認済み投稿50件の収集が必要（圭一郎さんとの作業）
- note社への問い合わせを実施推奨（テンプレート準備済み）
- 未決定事項: 評価モデル選定、自動再生成閾値はデータセット構築後に決定

## 2026-04-09

### 実施内容
- イベント投稿シート（X・IG両方）に「画像リンク」「画像表示」列を追加（IMAGE関数で自動サムネイル表示）
- 圭一郎さんメール確認（2通）: IGイベント投稿へのフィードバック + カンガルーカップ2026情報
- IGイベント投稿シート一括修正（46セル更新）:
  - No.1: 第90期→第88期
  - No.4: 4月オンライン講座→延期（5月開始）
  - No.5: 体験WS→満員御礼+5月募集構成に修正
  - No.8: カンガルーカップ→岐阜メモリアルセンター、活動紹介トーンで記事作成
  - No.12,20,25: オンラインWS費用¥4,000→¥3,000に修正、5月初回強調
  - No.13,14: 告知不要に変更
  - No.15: 太陽食品コラボ6月→6/5-6/6の2日間に修正
  - No.16: 第91期→第89期
  - No.21: 抗加齢医学学会→学会発表の告知記事作成
- Xイベント投稿シート修正+追加:
  - Row2 オンライン講座→延期、Row8 第91期→第89期
  - 6件追加: カンガルーカップ、オンラインWS 5-7月、太陽食品6月、抗加齢医学学会
- カンガルーカップ公式HP情報取得（会場: 岐阜メモリアルセンター、選手へのサウンドヒーリングサポート提供）

### 成果
- IGイベント投稿: 25件中11件修正、2件告知不要、12件変更なし
- Xイベント投稿: 既存2件修正 + 6件新規追加（計14件）
- 全記事の確認メモ列に「対応済」ステータスを記載
- メモリ4ファイル保存（フィードバック、カンガルーカップ、オンラインWS正式情報、打ち合わせ予定）

- Xイベント投稿シートの既存記事修正+不足イベント6件追加（計14件に）
- カンガルーカップ添付資料6件をダウンロード・ローカル保存（イベント資料/カンガルーカップ2026/）
  - SNS用DOCX、開催要項PDF、写真4枚
- DOCX・PDFから詳細情報を抽出:
  - 正式日程: 4/27(月)〜5/3(日)（当初4/28-5/2から修正）
  - 会場: 長良川テニスプラザ（ハードコート13面）
  - 賞金総額US$100,000
  - 昭和西川ムアツマット×KITAサウンドヒーリングのセルフケアコーナー設置
  - 選手リカバリーケアとして体感音響・自然音を提供
- IG・X両方のカンガルーカップ記事を正式情報で更新

### 課題・備考
- 自由が丘打ち合わせの日程返信が必要（4/14 or 15）
- カンガルーカップ出場選手発表は4/15頃 → 発表後にSNS投稿内容を更新する可能性あり
- カンガルーカップ資料のDriveアップロード未完了（サービスアカウントにストレージ制限あり。手動アップロードが必要）

## 2026-04-08

### 実施内容
- イベント投稿専用シート作成（「Xイベント投稿」「IGイベント投稿」タブをスプレッドシートに追加）
- Googleカレンダー(keiichiro.kita@gmail.com) 4〜7月の全イベント取得・照合
- 公式サイト(sound-healing.jp)・チラシ・イベント資料と突き合わせて照合レポートPDF作成
- IGイベント投稿記事25件を情報確認ステータス付きで一括作成（✅公式確認済13件/⚠️要確認7件/❓未確認5件）
- 圭一郎さんへ確認依頼メール送信（確認事項6項目）
- X自動投稿にリプライ機能を実装（K列「リプライテキスト」追加、投稿後5秒待機→自動リプライ）
- 即時投稿コマンド `post_now.sh` 追加（GitHub Actionsの遅延を回避）
- Day4投稿実行（X: ここちよい音の日+リプライ / IG: 体感音響カルーセル3枚）
- Cloudflare R2セットアップ完了（サブスクリプション有効化→バケット作成→Public URL有効化→APIトークン発行）
- GitHub Secretsに R2環境変数5件登録（R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL）
- R2接続テスト成功（アップロード→公開URL→削除の全フロー確認）
- IGカルーセルテスト投稿成功（3枚: 1920x1080, 800x1200, 500x500）
- IG投稿のリサイズ処理を無効化（元サイズで投稿に変更）
- 汎用画像リサイズツール `tools/image_resizer.py` として独立化（プリセット10種対応）
- .envにR2環境変数追加

### 成果
- イベント照合レポート: `イベント照合レポート_2026-04-08.pdf`（4ページ、公式ソース付き）
- IGイベント投稿: 25件作成完了、圭一郎さん確認待ち
- リプライ機能: コミット `6fa704b` でpush済み、Day4で動作確認済み
- 即時投稿: コミット `cf9f475` でpush済み
- Cloudflare R2: バケット `shc-sns-temp-images`（APAC）稼働中
- Public URL: `https://pub-b525379228434e46a50c4d3f1edae5c7.r2.dev`
- IG投稿パイプライン: Google Drive画像→R2アップロード→IG API投稿→R2削除の全フロー動作確認済み
- コミット: `ed51ef0`

### 課題・備考
- 圭一郎さんからのイベント確認回答待ち（⚠️要確認7件/❓未確認5件）
- 確認後: IG記事修正 → X記事作成の流れ
- GitHub Actions schedule cronは遅延が大きい（今回13:40予約→14:53実行）。正確な投稿には `./post_now.sh` を使用
- IGグリッド表示では4:5画像が1:1クロップされるため、リサイズは無効化し元サイズ投稿に変更
- resize_for_ig()関数はコード内に残存（将来再利用可能）
- 今後のシステム構築時は既存OSS調査+Codex壁打ちを設計プロセスに組み込む方針を決定

## 2026-03-10（ミーティング方針決定・イベント資料保存）

### ミーティング議事録PDF作成
- NotebookLMの録音トランスクリプト + Gmailの講座名提案を統合
- `generate_meeting_pdf.py` で11ページのPDF生成 → `ミーティング議事録_20260310.pdf`
- 主な決定事項:
  - ターゲット: 30〜50代女性（子育て中〜終えた層）
  - オンライン講座設計: 無料体験→有料コース（月額制）
  - 集客ファネル: Instagram → LINE → Zoom体験 → リアル体験会 → 資格取得
  - YouTube戦略: 自然音BGM長尺動画で再生時間を稼ぐ
  - 講座名候補: 圭一郎さんから複数案提示（「音の健康法」「Harmonic Self Care」等）

### イベント資料保存
- 「ここちよい音の日」チラシPDF 2点をGmailからダウンロード・保存
  - `イベント資料/ここちよい音の日_20260402-04/★チラシ：太陽食品＆SH協会のコラボ企画 『ここちよい音の日』2026.4.2-4.pdf`（4.5MB・表面）
  - `イベント資料/ここちよい音の日_20260402-04/★チラシ裏面　2026.4.2-4.pdf`（842KB・裏面）
- イベント概要:
  - 太陽食品世田谷店 & SH協会コラボ
  - 2026年4月2日(木)・3日(金)・4日(土) 13:00〜16:00
  - 体験500円（オーガニック試飲付）
  - KITAサウンドヒーリング体験（約10分の肩腰ケア）

### オンライン講座告知案（Gmailより保存）
- 圭一郎さんからの転送メール「4月の新オンライン講座スタート」を確認
- 講座名決定: **「音のウェルビーイング」オンライン Harmonic Science 体験講座**
- サブタイトル: 世界の自然音と呼吸で整えるセルフケア
- 日程:
  - 4月14日（火）10:00〜12:00（Zoom・4,000円）
  - 4月23日（木）10:00〜12:00
- 「音の旅シリーズ」4テーマ: 森の音と呼吸 / 海の音と声 / 風の音と瞑想 / 夜の音と深い呼吸
- 保存先: `イベント資料/オンライン講座_202604.md`

### スターライトヒーリング追加公演情報（Gmailより保存）
- 圭一郎さんからのメール「スターライトヒーリングマラマハワイ追加公演決定」を確認
- イベント: **Star Light Healing Malama Hawaii** 追加公演
- 日程: 2026年4月12日（日）13:30〜14:20
- 会場: さいたま市宇宙劇場（JACK大宮3階）
- 料金: 大人620円 / 小人310円
- 後援: ハワイ州観光局
- チラシ画像2点を保存:
  - `イベント資料/スターライトヒーリング_20260412/★さいたま市star_light_healing_2025.jpg`（3.0MB・表面）
  - `イベント資料/スターライトヒーリング_20260412/★star_light_healing_2025_v4_fix_ura.jpg`（2.8MB・裏面）
- イベント情報: `イベント資料/スターライトヒーリング_20260412/イベント情報.md`

---

## 2026-03-09（NotebookLM共有ノートブック確認・SNS方針反映）

### NotebookLM ノートブック調査

#### 確認結果
- 圭一郎さん（keiichiro.kita@gmail.com）から**28件のNotebookLM招待**がGmailに到着
- ソース: ミーティング録音（m4a）、YouTube動画等をNotebookLMにアップロードしたもの
- ✅ **全28件受諾完了**（Gmail招待リンク経由で全件NotebookLMに追加済み）

#### 受諾済みノートブック（全28件）

**カテゴリA: サウンドヒーリング科学・メソッド（7件）**
1. Harmonic Healing: Breathing with Infinite Words — 呼吸法×サウンドクッション×骨伝導
2. Harmonic Healing: Autonomic Resilience through Sound and Vibration — 自律神経×音×振動
3. Sound Healing: Nature, Harmony, and Bone Conduction Methods — 自然音×骨伝導メソッド
4. Resonant Harmony: The Evolution of Sound Healing — サウンドヒーリングの進化
5. Harmony of the Body: Sound, Nature, and Self-Healing — 身体×自然×自己治癒
6. Sound Healing and the Resonance of Nature — 自然の共鳴
7. Resonating Wellness: Sound Therapy and the Cellular Flow of Life — 細胞レベルの音響療法

**カテゴリB: 自然音・地球の音アーカイブ（4件）**
8. The Resonant Soul of Nature — 自然の響き
9. The Healing Power and Global Branding of Japanese Nature Sounds — 日本の自然音ブランディング
10. Earth Sound Archives and the Spirit of Nature — 地球の音アーカイブ
11. Earthly Soundscapes and the Preservation of Natural Heritage — 自然遺産の保存

**カテゴリC: ビジネス・ブランディング・イベント（4件）**
12. Global Networking for Harmonic Healing Workshops — ワークショップネットワーク
13. Global Healing: Planning Interactive Amneck Online Workshops — オンラインワークショップ企画
14. Taiyo Foods and Sound Healing Association Collaborative Event 2026 — 太陽フーズコラボ
15. Sonic Branding and Sleep Environments for Professional Athletes — アスリート睡眠環境

**カテゴリD: 哲学・スピリチュアル・意識（7件）**
16. Awakening the Divine Genetic Blueprint for 2026 — 遺伝子の覚醒
17. The Sound of Self-Love and Inner Resilience — 自己愛と内なる回復力
18. The Sound of Universal Grace: Cultivating the Inner Mother — 宇宙の恩寵
19. Spiritual Independence Through Mindful Association Content — スピリチュアル自立
20. The Creative Power of Language and Resonance — 言葉と共鳴の創造力
21. Eternal Presence and the Dawn of Open Contact — 永遠の存在
22. Awakening the Divine Blueprint for 2026 — 神聖な青写真

**カテゴリE: AI・テクノロジー・アート（3件）**
23. The Harmony Place: Cultivating Human Sensibility in the AI Age — AI時代の人間感性
24. The Vibration of Intelligence: Resonance Beyond AI — AI超越の振動
25. The Vibration of Being: Art, Consciousness, and Cosmic Resonance — 宇宙的共鳴

**カテゴリF〜H（各1件）**
26. The Resonance of Physical Joy and Emotional Peace — ウェルビーイング
27. The Art of Nature and the Nature of Art — イェール大学シンポジウム
28. Guide to the School Public Transmission Compensation System — 法律・制度

#### SNS戦略への反映ポイント
- **高優先**: アスリート×睡眠×自然音（企業案件テーマ）、呼吸法メソッド（実践系コンテンツ）
- **中優先**: AI時代の感性論、自然音グローバルブランディング
- **note向け**: バイブレーション哲学、静寂と真の音、芸術×科学の融合

#### 保存場所
- `NotebookLM_アップロード用/NotebookLM_ノートブック一覧.md` に全28件の一覧・分類・詳細・方針を保存

#### 既存ノートブック（マイノートブック）も確認
- 協会誌シリーズ（2011-2025）: 計107ソース
- 自然音・体感音響 解説①②: 計55ソース
- 学術論文・学会発表: 38ソース
- 体験談・事例集: 8ソース
→ これらと新規ノートブックを組み合わせた深いSNSコンテンツ制作が可能

### 次のアクション
1. ~~残り23件のNotebookLM招待を受諾~~ ✅完了
2. ~~各ノートブックの内容確認・概要追記~~ ✅完了（全28件の概要・SNS活用案を追記済み）
3. 確認内容をInstagram/X/note投稿計画に反映
4. アスリート×睡眠テーマを企業案件カテゴリの新規SNSシリーズとして企画
5. 太陽フーズイベント（2026.4.2-4「ここちよい音の日」）の告知コンテンツを早急に準備
6. X API クレジット購入の判断（圭一郎さんに確認）
7. Instagram/LINE APIセットアップ（圭一郎さんの依頼事項完了待ち）

---

## 2026-03-09（X API セットアップ完了・課金確認）

### X Developer Console セットアップ

#### 完了項目
- Developer登録完了（アカウントID: 2029826061224267778）
- アプリ作成済み: 「2029826061224267778SFH_Science」（App ID: 32523502, Status: ACTIVE）
- ユーザー認証設定: Read+Write権限、ウェブアプリ/ボット、コールバックURI設定済み
- 全認証情報取得済み:
  - Bearer Token
  - Consumer Key (API Key + API Secret)
  - Access Token + Access Token Secret（@SFH_Science用、Read+Write権限）
  - OAuth 2.0 Client ID + Client Secret
- `.env` ファイル作成済み（sns-auto-poster/.env）
- 認証テスト成功: `@SFH_Science`（サウンドヒーリング協会）として認証確認

#### 課題: API クレジット不足
- X API は「Pay Per Use」方式に移行済み
- 現在のクレジット残高: **$0.00**
- ツイート投稿（POST /2/tweets）には**クレジット購入が必要**（402 Payment Required）
- 認証・読み取り（GET）は成功するが、書き込み（POST）は有料
- → クレジット購入（最低$5〜）の判断が必要

### 次のステップ
1. X API クレジット購入の判断（圭一郎さんに確認）
2. 圭一郎さんへの依頼事項実施（下記参照）
3. Instagram API / LINE API セットアップ

---

## 2026-03-06（Instagram API セットアップ調査）

### 調査結果

#### Facebookページ確認
- **ページ名**: サウンドヒーリング協会 The Society for Harmonic Science
- **URL**: https://www.facebook.com/harmonicscience
- **フォロワー**: 601人
- **カテゴリ**: 団体
- ※既存ページあり。管理者は圭一郎さん（推定）

#### Instagramアカウントセンター確認
- @harmonicscience_jp はビジネスアカウント（確認済み）
- Facebookページとは**未接続**
- アカウントセンターにInstagramのみ表示、Facebookアカウント未追加

### 圭一郎さんへの依頼事項（まとめて実施）

以下3点を圭一郎さんに依頼する必要あり：

1. **Facebookページの管理者追加**
   - 「サウンドヒーリング協会」Facebookページ（https://www.facebook.com/harmonicscience）に康二郎さんのFacebookアカウントを管理者として追加
   - 手順: Facebookページ → 設定 → ページの役割 → 管理者を追加

2. **InstagramとFacebookページの接続**
   - @harmonicscience_jp を「サウンドヒーリング協会」Facebookページに紐付け
   - 手順: Instagramアプリ → 設定 → ビジネスツールと管理 → リンク済みのアカウント → Facebook → ページを選択
   - ※圭一郎さんのFacebookアカウントでInstagram管理権限がある場合はそちらから実施

3. **Facebook Developer登録（オプション）**
   - https://developers.facebook.com/ で開発者登録
   - 電話番号認証が必要
   - ※康二郎さんのFacebookアカウントでも可（ページ管理者に追加後）

4. **LINE公式アカウントのログイン情報確認**
   - LINE公式アカウント（@868hqnfw）の管理画面ログインに使ったアカウント情報を共有
   - 管理画面: https://manager.line.biz/
   - Messaging API有効化のためにログインが必要

### 依頼後に康二郎さんが行う作業
- Facebook Developer Appの作成
- Instagram Graph APIの権限追加
- アクセストークン生成
- `.env` ファイルへの設定

---

## 2026-03-02（SNS Auto Poster: Instagram API実装・コンテンツ変換）

### 実施内容

#### 1. 環境構築・ビルド修正
- `date-fns-tz` v2→v3 にアップグレード（date-fns v3との互換性）
- `@line/bot-sdk` v9 の型定義変更に対応
  - 旧 `Message` 型と新 `messagingApi.Message` 型の互換性問題を修正
  - `getNumberOfFollowers` → `getFollowers` APIに移行
- `twitter-api-v2` の `media_ids` タプル型修正
- 未使用import一掃（`isBefore`, `logger` in test scripts）
- `npm run build` ゼロエラー達成

#### 2. Instagram Graph API 実装（Phase 5完了）
- `src/platforms/instagram.ts` フル実装
  - 単一画像投稿: コンテナ作成 → ステータス確認 → 公開の3ステップ
  - カルーセル投稿: アイテムコンテナ → カルーセルコンテナ → 公開
  - キャプション整形（2200文字制限、ハッシュタグ30個制限）
  - 認証確認（`verifyCredentials`）
  - アカウント情報取得（`getAccountInfo`）
- `src/platforms/index.ts` にInstagramハンドラー登録
- `src/scripts/test-instagram.ts` テストスクリプト作成

#### 3. コンテンツ変換スクリプト
- `src/scripts/convert-content.ts` 作成
  - X投稿90本.md → 90件のYAMLファイル
  - Instagram投稿48本.md → 13件のYAMLファイル（キャプション付きのみ）
  - 合計103件のスケジュール済みYAMLファイル生成
  - 2026-03〜05の3ヶ月間にスケジュール配置

#### 4. 動作検証
- `npm run build` — ゼロエラー
- `npx tsx src/scripts/convert-content.ts` — 103ファイル生成成功
- `npm start` — メインフロー正常動作（104投稿読み込み、0件投稿対象）

### 生成ファイル
| ディレクトリ | ファイル数 | 内容 |
|-------------|-----------|------|
| content/posts/2026-03/ | 42 | X + Instagram投稿 |
| content/posts/2026-04/ | 30 | X投稿 |
| content/posts/2026-05/ | 31 | X + Instagram投稿 |

### Phase完了状況
| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 1 | プロジェクト構築 | ✅ 完了 |
| Phase 2 | Twitter API | ✅ 完了 |
| Phase 3 | LINE API | ✅ 完了 |
| Phase 4 | スケジューラー | ✅ 完了 |
| Phase 5 | Instagram API | ✅ 完了 |

### 次のステップ
- [ ] Instagram APIのアクセストークン取得・.env設定
- [ ] 各プラットフォームの認証テスト実行
- [ ] 画像URLの準備（Instagram投稿用に公開URLが必要）
- [ ] GitHub Actionsの定期実行テスト

---

## 2026-02-24（noteアカウント開設・海外展開調査）

### 実施内容
- **noteアカウント開設完了**
  - アカウント名: サウンドヒーリング協会
  - メール認証: 完了
  - 投稿可能状態

### 海外展開調査結果

#### noteの海外対応状況
- 2026年2月〜: 自動多言語対応機能テスト開始予定
- GoogleのAI翻訳で英語など多言語に自動変換
- 現時点では日本国内向けサービスがメイン

#### 海外向け代替プラットフォーム
| プラットフォーム | 特徴 | 用途 |
|-----------------|------|------|
| **Medium** | 海外版note的存在、SEO強い | 英語圏への情報発信 |
| **Substack** | ニュースレター特化 | ファンとの深い関係構築 |

#### Instagram/X/YouTube 海外向け戦略
- **Instagram**: ビジュアル中心で言語の壁を超えやすい。日英併記キャプション推奨
- **YouTube**: タイトル・説明文の翻訳追加、字幕設定が重要
- **X**: 英語ハッシュタグ活用（#soundhealing #naturetherapy #meditation）

#### 推奨戦略（2段階）
```
【Phase 1】国内基盤構築（現在）
├── note: 日本語コンテンツ蓄積
├── Instagram/X/YouTube: 日本語メイン
└── LINE: 国内会員向け

【Phase 2】多言語展開（今後）
├── Medium: 英語記事（noteの翻訳版）
├── Instagram: 日英併記キャプション
├── YouTube: 字幕・翻訳タイトル追加
└── X: 英語ハッシュタグ追加
```

### 次回やること
- [ ] noteプロフィール設定（アイコン、自己紹介、URL）
- [ ] note初回記事投稿
- [ ] Medium アカウント作成検討

### 開設済みSNSアカウント一覧
| プラットフォーム | アカウント | 状態 |
|-----------------|-----------|------|
| Instagram | @harmonicscience_jp | 開設済み |
| X | @SFH_Science | 開設済み |
| LINE公式 | @868hqnfw | 開設済み |
| note | サウンドヒーリング協会 | **本日開設** |

---

## 2026-02-24（ミーティング議事録確認・海外展開追加）

### 実施内容
- NotebookLMで新規ミーティング議事録を確認
- 海外展開をPhase 11としてタスクシートに追加
- 将来目標・参考情報セクションを追加

### ミーティング議事録要点（Sound Healing Association Marketing Strategy）

#### 1. 広報戦略（SNS・NotebookLM活用）
- **信頼性向上**: 医療関係者のバックアップ、訴訟・事故ゼロの実績を前面に
- **体験談公開**: 薬機法に配慮しつつ実例を発信
- **既存コンテンツ再利用**: CD付き書籍など過去コンテンツをSNSで公開

#### 2. NotebookLM活用アイデア
- 長時間動画（2時間等）を要約 → SNS宣伝文句に活用
- 協会の資料フォルダを公開 →「自由に使ってください」形式

#### 3. 新規ターゲット拡張
- **海外発信**: イタリア、ウズベキスタン、台湾など既に需要あり → 英語化検討
- **法人向け（BtoB）**: ホンダ、パナソニック、第一興商との関係活用 → 企業向けワークショップ

### 更新ファイル
- タスクシート_SNS収益化.md: Phase 11（海外展開）追加、将来目標セクション追加

---

## 2026-02-24（コンテンツ制作完了）

### 実施内容
- 3ヶ月分の全SNSコンテンツ下書き作成完了
- 2セッション並行作業体制を構築

### 作成ファイル（コンテンツ/フォルダ）

| ファイル | 内容 | 本数 |
|----------|------|------|
| X投稿90本.md | 科学データ・名言・告知・シェア | 90本 |
| Instagram投稿48本.md | カルーセル・単画像・リール・告知 | 48本 |
| note記事12本.md | 無料8本・有料4本 | 12本 |
| LINEステップ配信7通.md | 登録〜7日目の自動配信 | 7通 |
| YouTube動画24本.md | BGM・解説・実践・イベント | 24本 |

### コンテンツ総数
- **合計: 181本 + LINE7通**
- すべて資料まとめ_API処理結果.mdの科学データを活用
- ターゲット（40-60代女性）を意識した内容

### YouTube動画構成
| カテゴリ | 本数 | 特徴 |
|----------|------|------|
| 自然音BGM（長尺） | 6本 | 1〜3時間、再生時間稼ぎ |
| 解説・教育 | 8本 | 台本付き |
| 実践ガイド | 6本 | 一緒にやる形式 |
| イベント記録 | 4本 | ダイジェスト |

### 次のステップ
- 別セッションでSNSアカウント開設進行中
- コンテンツの最終調整・画像制作
- 投稿スケジューラー設定

---

## 2025-02-24

### 実施内容
- SNS収益化フローチャートを再作成・提示
- 投稿頻度と3ヶ月分コンテンツ量を算出
- YouTube立ち上げプランを策定
- mocca-projectのタスク管理形式を参考にプロジェクト構造を整備

### 作成ファイル
1. **タスクシート_SNS収益化.md**
   - 全体タスク管理（Phase 1-5）
   - プラットフォーム別コンテンツ量
   - KPI目標設定

2. **タスクシート_YouTube.md**
   - YouTube専用タスク管理
   - 24本の動画コンテンツ計画
   - 収益化ロードマップ

3. **PROJECT_STANDARDS.md**
   - ドキュメント構成ルール
   - タスク管理ルール
   - コンテンツ制作ルール

### 3ヶ月分コンテンツ量（確定）
| プラットフォーム | 頻度 | 本数 |
|------------------|------|------|
| X | 毎日 | 90本 |
| Instagram | 週4回 | 48本 |
| YouTube | 週2回 | 24本 |
| note | 週1回 | 12本 |
| LINE | 週1回 | 12本 |
| **合計** | | **186本** |

### 成果
- プロジェクト管理構造がmocca-project形式に統一
- Phase別タスク分解により作業分担が可能に

### 次のステップ
- Phase 1: 各プラットフォームアカウント開設
- Phase 2: コンテンツ一括制作開始

---

## 2025-02-24（追加作業）

### 実施内容
- 代表・圭一郎さんとの会話内容を確認（NotebookLM音声記録）
- 長期目標・ビジョンをタスクシートに反映

### 圭一郎さんとの会話要点
1. **最終目標**: 資格を取得する実践者（セラピスト）を増やす
2. **ターゲット**: 40代〜60代女性（子育てを終えた層）
3. **核心メッセージ**: 病院に頼らず「自己回復力」を高める知恵
4. **ブランディング課題**: 「サウンドヒーリング」が怪しいと思われがち
5. **対策**: 科学的・歴史的根拠を前面に、既存書籍のデジタル化

### 成果
- タスクシート_SNS収益化.md に以下を追加：
  - メインターゲット（40-60代女性）
  - 長期目標セクション（Phase 6-10）
  - ブランディング方針

### 追加したPhase（今後の目標）
| Phase | 内容 | 時期 |
|-------|------|------|
| Phase 6 | 体験会誘導強化 | Month 4-6 |
| Phase 7 | 継続学習コミュニティ構築 | Month 6-9 |
| Phase 8 | スキルアップ体系化 | Month 9-12 |
| Phase 9 | 資格制度準備 | Year 2 |
| Phase 10 | 実践者ネットワーク拡大 | Year 2-3 |

---

## 2025-02-23

### 実施内容
- 2022年〜2025年の協会誌PDF読み込み状況を確認
- 資料まとめ.mdに既に2022年〜2025年の情報が整理済みであることを確認

### 確認した協会誌（2022年〜2025年）
1. **vol32-33 (2021年 20周年記念号)** - 目次・活動実績まとめ
2. **vol34-35 (2022年)** - 「地球の声に耳を傾けよう」
   - 変革期の自分軸、トランスパーソナルセルフ、音の糧
3. **vol35-36 (2023年)** - 「かんむり座のカムイとうしかい座のアルクトゥルス」
   - 中村泰治会長逝去、スターライトヒーリングの歴史
4. **vol37-38 (2024年)** - 「自分を信じる時代」
   - 研修会実績、日本の医療費問題、OECD比較データ
5. **vol39-40 (2025年)** - 「私たちに満ちる大自然の力を育もう」
   - 宇宙と天体、音の振動原理、新しい周期の到来

### 成果
- 資料まとめ.mdは2011年〜2025年の協会誌情報が完備
- SNS投稿用の画像情報も整理済み

### 次のステップ
- SNSコンテンツの作成開始

---

## 2025-02-23（追加作業）

### 実施内容
- サブフォルダ内の未処理資料を確認・処理
- 資料まとめ_API処理結果.mdに追記

### サブフォルダ構成（171ファイル）
1. **2.10 -1　　４３本/**
   - 音の効果事例体験談１７本
   - 原稿　様々１５本
   - 雑誌ほかメディア５本
   - CD　MuAtsu CD　６本

2. **2.10 -2　５２本/**
   - 骨密度４本
   - 体感音響１５本
   - 自然音実験エビデンス１６本
   - ポスターほか１4本

3. **2.9 　58本/**
   - スターライトヒーリング２２本
   - CD book 本３６本

### 追加処理した重要資料

#### 実験・エビデンス系
1. **水道水に60分自然音を聞かせる実験（2021年）**
   - 東洋化学株式会社 中島俊樹
   - 400倍拡大画像で水の構造変化を視覚化
   - 残留塩素の害作用を解除

2. **植物に及ぼす自然音の効果（2008年）**
   - 第25回生命情報科学シンポジウム
   - 奥健夫、喜田圭一郎、中村泰治
   - 菊の花48日間実験：自然音で生命力維持

3. **自律神経機能への影響（2016年）**
   - 被験者9名（12歳〜48歳）
   - 副交感神経・交感神経両方の機能向上を確認

4. **骨密度への影響（2012年）**
   - 田園調布 長田整形外科
   - 6ヶ月後の骨密度上昇を確認（70代・80代女性）

#### イベント系
5. **スターライトヒーリング マラマハワイ（2024年）**
   - さいたま市宇宙劇場
   - 累計1,400名以上来場
   - ハワイ州観光局後援

### 成果
- 資料まとめ_API処理結果.mdにサブフォルダ資料を追記完了
- SNS活用に最適なエビデンス資料を特定

---

## 2025-02-06

### 実施内容
- 資料フォルダ内の協会誌PDF（2011年〜2021年）を読み込み
- 資料まとめ.md を作成（重要情報を整理）

### 読み込んだ資料
1. 2011協会誌p2-p3.pdf - Peace Creating Trip to New York
2. 2012P2-P3_喜田sam3.pdf - 言葉と音の力
3. 2013 vol16-17_P2-P3_sam1.pdf - 自分の維新と攘夷
4. 2014 vol18-19_P2-P3_.pdf - 私のウエルビーイングライフ（喜田氏自伝）
5. 2015 P2-P3_Harmonic Revolution 2015.pdf - 3つのメソッド詳細
6. 2016協会誌P2-P3.pdf - 新しい生き方（ゲイナー博士逝去報告）
7. 2017 vol24-25 和らかい心と柔らかな体.pdf - ホクレア号、アカカさん
8. 2018自分を動かす力.pdf - 日野原先生との関係、カリブ海クルーズ
9. 2019 sh_vol28-29_data_P2-P3_sam3.pdf - 会社設立の歴史詳細
10. 2020 p2-p3 Journal vol30-31.pdf - ライフフォース概念
11. 2021 SH協会20周年 p4-5.pdf - 20周年挨拶

### 成果
- 資料まとめ.md に以下を整理：
  - 会社・団体の歴史年表
  - 喜田圭一郎理事長プロフィール
  - 3つのメソッドの詳細
  - 重要人物（ゲイナー博士、日野原先生、アカカさん等）
  - 理念・コンセプト
  - 引用される思想家・研究者一覧
  - キーワード・フレーズ

### 残り資料
- 2022年〜2025年の協会誌PDF（6ファイル）
- 2008年〜2010年のdocファイル（3ファイル、バイナリで読み込み不可）

---

## 2025-02-05

### 実施内容
- プロジェクト初期セットアップ
- GitHubルール（CLAUDE_INSTRUCTION.md）の確認
- サウンドヒーリング協会サイト（https://www.sound-healing.jp/）の調査
  - サイト構造、メニュー、コンテンツの把握
  - 定期イベント情報の確認
  - 既存メディア（YouTube、Facebook、協会誌）の確認
- ジョイファンデーションサイト（https://www.h-garden.com/）の調査
  - 会社概要、事業内容の把握
  - 製品情報（小型体感音響）の確認
  - 取引先情報の確認

### 成果
- 両団体の関係性を理解
  - NPO: 理念・研究・教育
  - 株式会社: 製品化・商用サービス
- 広報に活用できるコンテンツの把握
  - 定期イベント（Harmonic Day、ここちよい音の日など）
  - 製品（小型体感音響 Harmonic Massage）
  - スターライトヒーリング マラマハワイ
- プロジェクト基盤ファイル作成（README.md、CLAUDE.md、DEVLOG.md）

### 課題・備考
- SNS戦略の具体的な計画策定が必要
- 公式LINE構築の検討
- 投稿コンテンツのテンプレート作成が必要
