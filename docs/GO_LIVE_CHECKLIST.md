# 運用開始前チェックリスト (WEB-030)

Phase 1 の本番運用開始前に、Claude 側で手動実施するチェック項目。すべて Green になったら内部運用開始。

## 前提: 本番環境の準備

- [ ] Vercel プロジェクト作成・GitHub 連携済み
- [ ] Railway プロジェクト作成（api / celery-worker / celery-beat / Redis）
- [ ] Supabase Cloud プロジェクト作成・マイグレーション反映済み
- [ ] Cloudflare R2 バケット作成・公開 URL 設定済み
- [ ] `docs/ENV_VARS.md` に従って各レイヤの env 投入完了
- [ ] GitHub Actions 変数 `VERCEL_ENABLED=true` / `RAILWAY_ENABLED=true` をセット

## 1. 疎通確認

- [ ] `curl -sf https://<railway-api>/health` が `{"status":"ok"}` を返す
- [ ] `https://<vercel>/` で `/login` が開く
- [ ] `https://<vercel>/login` から自社アカウントでログインできる
- [ ] `https://<vercel>/calendar` が 200 で開く

## 2. 認証 & SNS 接続

- [ ] 新規ユーザー登録（自社テスト用）
- [ ] ログアウト → ログイン往復
- [ ] 無効パスワードでエラー表示
- [ ] `/settings/sns` で X アカウントを **接続**（OAuth 往復）
- [ ] 同画面で IG アカウントを **接続**（OAuth 往復）
- [ ] `sns_accounts.is_active=true` が Supabase 側に記録される

## 3. 投稿機能

- [ ] `/create` で X のみ選択した投稿を即時投稿 → 実際に X に現れる
- [ ] `/create` で IG のみ選択・画像 1 枚で即時投稿 → IG に現れる
- [ ] IG カルーセル（2〜10 枚）で即時投稿 → IG に正しく現れる
- [ ] 予約投稿（5 分後）を設定 → 時刻通りに自動投稿される
- [ ] 予約投稿が `posts.status=published` に遷移する
- [ ] 失敗ケース（わざと画像なしで IG 投稿）→ `posts.status=failed` で記録される

## 4. メディア

- [ ] `auto_resize_ig=true` 付き画像アップロードで 4:5 (1080x1350) に変換されている
- [ ] R2 に `post-media/{org_id}/YYYY/MM/DD/{uuid}.jpg` で保存される
- [ ] パブリック URL を直接ブラウザで叩いて閲覧可能
- [ ] 10MB を超える画像で `413 Request Entity Too Large` が返る
- [ ] 11 枚以上同時アップロードで `400` が返る

## 5. 通知

- [ ] 投稿成功後、数秒以内に自社 SMTP 宛てに「投稿成功」メールが届く
- [ ] 投稿失敗時、同様に「投稿失敗」メールが届く
- [ ] 一部失敗（X 成功 + IG 失敗等）で「投稿一部失敗」メールが届く
- [ ] `/notifications` ページで通知履歴が表示される
- [ ] ベルアイコンの未読バッジが更新される
- [ ] WebSocket が切断 → 再接続（exponential backoff）される

## 6. D&D / カレンダー

- [ ] `/calendar` で下書きサイドバーの draft をカレンダー日セルにドロップ
- [ ] ドロップ後、`posts.status=scheduled` + `scheduled_at=12:00 JST` になる
- [ ] 検索・プラットフォームフィルタが動作

## 7. OAuth 再接続テスト

- [ ] `/settings/sns` で X を切断（`is_active=false`）
- [ ] 再度「X を連携」でフローが完了する
- [ ] IG についても同様に往復できる

## 8. バックアップ / ロールバック

- [ ] Supabase 自動 backup が有効化されている
- [ ] `supabase db dump` を手動実行してバックアップ SQL を取得できる
- [ ] Vercel Dashboard で旧デプロイを Promote する手順をリハーサル（切り戻しが 1 分以内）
- [ ] Railway Dashboard で旧リビジョンを Redeploy する手順をリハーサル

## 9. CI / デプロイ

- [ ] `main` への push で CI が走る（`.github/workflows/ci.yml`）
- [ ] `.github/workflows/deploy-frontend.yml` が Vercel にデプロイする
- [ ] `.github/workflows/deploy-backend.yml` が Railway にデプロイする
- [ ] `e2e.yml` は `run-e2e` ラベルで opt-in 実行できる

## 10. 観測 & 運用

- [ ] `docs/OPS_RUNBOOK.md` の日次チェック項目すべてが即座に参照できる
- [ ] Railway logs で `success/failed` を grep できる
- [ ] Slack / メール等で障害時の連絡先が定まっている
- [ ] `docs/KPI.md` の計測基準を理解している

## 11. launchd 並走

- [ ] 既存 `scripts/com.joyfoundation.sns-auto-poster.plist` が稼働継続
- [ ] Google Sheets に `Webアプリ化済` 列を追加し、Web アプリ版で投稿した行にマーク
- [ ] 2 週間無事故なら launchd 停止予定日をカレンダーに入れる

---

## 合格条件

上記 9 割以上が ✅ かつ、1〜11 章のうち **1 章も Red が残っていない** 状態で本番運用開始。
