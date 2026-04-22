# 運用ランブック (WEB-030)

Phase 1 の本番運用を担当する人向けの運用手順書。

## 1. 日次チェック

毎朝 10 分でできる確認。

| 項目 | 確認方法 | 正常値 |
|---|---|---|
| API 稼働 | `curl -sf https://<railway-api>/health` | `{"status":"ok"}` |
| Celery worker | Railway Dashboard → `celery-worker` | ログに `celery@...ready.` |
| Celery beat | Railway Dashboard → `celery-beat` | ログに `Scheduler: Sending due task check_scheduled_posts` |
| 予約投稿件数 | 管理者アカウントで `/calendar` を開く | 未処理の `scheduled` が滞留していない |
| 通知メール | SMTP アカウントの送信済みボックス | 昨日分の `投稿成功/失敗` メールが存在 |
| フロント | `https://<vercel>/` | ログイン画面が 200 で返る |

## 2. ログ確認

### Railway logs

```bash
# ローカル CLI から
railway logs --service api --deployment latest
railway logs --service celery-worker --deployment latest --filter publish_post
railway logs --service celery-beat --deployment latest --filter scheduled_posts
```

### 注目する grep パターン

| パターン | 意味 | アクション |
|---|---|---|
| `publish_target.*success` | 投稿成功 | 正常 |
| `publish_target.*failed` | 投稿失敗 | トラブルシュート (3 章) |
| `rate.?limit` / `429` | X/IG レート制限 | 3.1 節 |
| `401.*token` / `invalid_grant` | OAuth 失効 | 3.3 節 |
| `ConnectionResetError` / `Supabase.*timeout` | DB 接続切れ | 3.4 節 |
| `SMTPException` | 通知送信失敗（投稿は成功扱い） | SMTP 設定確認 |

### Supabase logs

Dashboard → Logs → Postgres / Auth で絞り込む。`auth.users` への書き込み・RLS 拒否を観察。

## 3. トラブルシュート

### 3.1 X API rate limit (429)

**症状**: `publish_post` が `429 Too Many Requests` で失敗。

1. Railway logs で `publish_target.*429` を確認し、影響ユーザ/投稿を特定。
2. `posts.status` が `failed` に遷移していることを確認（自動リトライは未実装）。
3. X Developer Portal で rate limit window を確認。一般に 15 分で解放。
4. 必要なら `/posts/{id}/publish-now` を手動で叩いて再送。
5. 多発する場合は投稿テンプレートの分散（同時刻投稿を避ける）を検討。

### 3.2 IG Container ERROR

**症状**: `graph.facebook.com` が Container ステータス `ERROR` を返す。

1. Railway logs で `ig_publisher` 周辺のメッセージを確認。
2. よくある原因:
   - 画像の縦横比が 4:5 の範囲外 → アップロード時 `auto_resize_ig=true` を付けたか確認
   - 画像 URL が Facebook から取得不能（R2 パブリック URL の 403/404）
   - IG Business Account 権限失効
3. R2 パブリック URL を `curl -I` でブラウザなしで 200 取得できるか確認。
4. `sns_accounts.platform_account_id` が正しい IG Business Account ID か Supabase で確認。

### 3.3 トークン失効

**症状**: `401 invalid_token` / `invalid_grant`。

1. 該当 `sns_accounts.id` を Supabase で特定。
2. 影響ユーザに連絡し、`/settings/sns` から該当プラットフォームの **再接続** を依頼。
3. OAuth 再接続で新しい `access_token` が保存される。`refresh_token` がある場合は自動更新を試みるが、Phase 1 は手動再接続でカバー。

### 3.4 DB 接続切れ

**症状**: `ConnectionResetError` / `Supabase.*timeout` が連続発生。

1. Supabase Dashboard → Project Settings → Usage で接続数・CPU を確認。
2. Railway の `api` サービスを **Restart**。`celery-worker` も同様。
3. 復旧しない場合は Supabase のサポートチケットを開く前に、Postgres の接続プール設定を確認。

### 3.5 通知メール不達

**症状**: 投稿は成功しているのにメールが届かない。

1. Railway `api` logs で `notifier` / `SMTPException` を grep。
2. SMTP 設定（`SMTP_HOST` 等）が未設定 → 警告ログが出るが投稿本体は成功。
3. Gmail の場合、アプリパスワードの失効・2段階認証解除を確認。
4. 送信元ドメインの SPF/DKIM が整っていないとスパム判定される可能性あり。

### 3.6 Celery beat が止まった

**症状**: 予約投稿時刻が過ぎても `publish_post` が走らない。

1. Railway Dashboard → `celery-beat` の稼働状況を確認。
2. ログに `Scheduler: Sending due task` が出ているか確認（毎分出る）。
3. Redis が落ちていないか、Redis プラグインの ping を確認。
4. 再起動で回復するケースがほとんど。

## 4. バックアップ

### Supabase 自動 backup

- Supabase Cloud の Pro 以上で日次自動 backup が有効。無料プランは 7 日保持なので注意。
- Dashboard → Database → Backups で復元可能。

### 手動エクスポート

月 1 回、キーテーブルを SQL ダンプで保全:

```bash
supabase db dump \
  --db-url "postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres" \
  --schema public \
  --data-only \
  -f backups/$(date +%Y%m%d)_public_data.sql
```

機密性のため、取得後は即座に暗号化ストレージ（1Password / Drive 暗号化）へ移す。

## 5. インシデント対応

### 一次切り分けフロー

```
症状発生
   ↓
1. /health が 200？ ── No → Railway api サービス restart
   ↓ Yes
2. /calendar ログイン可？ ── No → Supabase Auth 状態確認
   ↓ Yes
3. 投稿が成功する？ ── No → 3 章の該当節へ
   ↓ Yes
4. 通知が届く？ ── No → 3.5 節
   ↓ Yes
(症状再現しないなら一時的な可能性。ログを保全して様子見)
```

### 連絡先テンプレート

```
件名: [Phase 1 運用] <症状を 1 行で>

発生時刻: YYYY-MM-DD HH:MM JST
影響範囲: 全ユーザ / 特定ユーザ(<email>) / 特定投稿(<post_id>)
現象:
  - <観測された現象>
  - <エラーメッセージ>
  - <Railway logs URL>

対応状況:
  - [x] 一次切り分け実施
  - [ ] 復旧作業
  - [ ] 原因究明
  - [ ] 再発防止

次の更新: HH:MM
```

## 6. launchd 版との並走方針

Phase 1 期間は既存の `sns-auto-poster/`（launchd 版）を safety net として稼働継続:

- Web アプリ版で投稿が成功した行は、Google Sheets の該当行に `Webアプリ化済` ステータスをマーク（重複投稿防止）
- `scripts/com.joyfoundation.sns-auto-poster.plist` は継続稼働
- Web アプリ版の投稿成功率が 2 週間にわたり 99% 以上を維持できたら、launchd 版の `launchctl unload` を実行して単独運用へ移行

launchd 停止手順:

```bash
launchctl unload ~/Library/LaunchAgents/com.joyfoundation.sns-auto-poster.plist
```

再開する場合は `launchctl load` で戻せる。

## 7. 週次レビュー

毎週月曜 30 分:

- 投稿成功率（KPI）確認 → [`KPI.md`](./KPI.md)
- 発生したエラーの総括
- 来週の改善アクション 1〜2 件決定
