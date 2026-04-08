# Cloudflare R2 セットアップ手順（IG Auto Poster向け）

## 1. バケット作成
1. Cloudflare Dashboardで **R2 Object Storage** を開く。
2. `shc-sns-temp-images`（任意）でバケット作成。
3. 公開配信用URLを用意する。
   - 開発・検証: `r2.dev` を有効化
   - 本番推奨: カスタムドメインを割り当て

> Instagram Graph APIの `image_url` には外部から取得可能なHTTPS URLが必要です。

## 2. APIトークン作成（最小権限）
1. **Manage R2 API tokens** からトークン作成。
2. 対象バケットに対して `Object Read` / `Object Write` を許可。
3. 発行後に以下を控える。
   - Access Key ID
   - Secret Access Key
   - Account ID

## 3. GitHub Secrets設定
リポジトリの **Settings > Secrets and variables > Actions** で以下を追加:

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_PUBLIC_URL`（例: `https://pub-xxxxxxxx.r2.dev` or `https://img.example.com`）

既存のIG用Secrets（`IG_ACCESS_TOKEN`, `IG_BUSINESS_ACCOUNT_ID`）も必要です。

## 4. アプリ側の動作
- `ig_auto_poster.py` は画像を4:5(1080x1350)にリサイズ後、R2へアップロード。
- 投稿処理の成否にかかわらず、アップロードした一時オブジェクトは削除。
- R2アップロード失敗時は `lh3.googleusercontent.com` URLへフォールバック。

## 5. 運用推奨
- 事故時の取りこぼし対策として、R2バケットにライフサイクルルール（例: 1日で削除）を設定。
- 将来のアプリ化では、`ig-temp/<yyyy>/<mm>/<dd>/...` のようなプレフィックス分離を継続。
- `R2_PUBLIC_URL` は末尾 `/` なしで管理する（コード側で吸収はしているが統一推奨）。

## 6. 動作確認
ローカルまたはGitHub ActionsでIG投稿を実行し、以下を確認:
1. R2へ画像が一時的に作成される
2. Instagram投稿が成功する
3. 投稿後にR2オブジェクトが削除される
4. R2無効時にlh3フォールバックで投稿が継続する
