# Codex壁打ち: Cloudflare R2による画像ホスティング統合

## 目的
Instagram Graph APIでの自動投稿時に、リサイズ済み画像を一時的にホストするためCloudflare R2を使用する。

## 背景
- IG Graph APIのContainer作成（POST /{ig-user-id}/media）では`image_url`パラメータに**公開アクセス可能なHTTPS URL**が必須
- Google Driveのプライベートリンクは使えない
- lh3形式（`https://lh3.googleusercontent.com/d/{file_id}`）は画像取得には使えるが、リサイズはできない
- Pillowで4:5（1080x1350px）白余白パディングのリサイズが必要
- リサイズ済み画像を公開URLで提供する必要がある

## 現在のig_auto_poster.pyの構造
```
ig_auto_poster.py (498行)
├── download_drive_image(drive_url) → PIL Image
├── resize_for_ig(img) → PIL Image (1080x1350, 白余白パディング)
├── upload_to_imgbb(img) → public URL （未使用、imgBBからR2に変更予定）
├── drive_url_to_lh3(drive_url) → lh3 URL
├── prepare_image_url(drive_url) → public URL（DL→リサイズ→アップロード→URL返却）
├── post_single_image(image_url, caption, token, account_id) → post_id
├── post_carousel(image_urls, caption, token, account_id) → post_id
├── get_scheduled_posts(ws) → posts list
├── run_scheduled(dry_run=False)
├── list_scheduled()
└── post_single_row(row_num)
```

## 要件

### 1. Cloudflare R2の設定
- R2バケット名の推奨（例: `shc-sns-temp-images`）
- バケットのパブリックアクセス設定（カスタムドメインまたはr2.dev URL）
- APIトークンの最小権限（R2読み書きのみ）

### 2. ig_auto_poster.pyの変更
- `upload_to_imgbb()` を `upload_to_r2()` に置換
- boto3（S3互換）でR2にアップロード
- アップロード後の公開URLを返す
- 投稿完了後にR2から画像を削除（クリーンアップ）
- 環境変数: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`

### 3. requirements.txtの更新
- boto3の追加

### 4. GitHub Actionsの更新
- R2関連のSecretsを追加
- .github/workflows/auto_post.yml にR2環境変数を渡す

### 5. アプリ化を見据えた設計
- R2のバケット構造（将来的にユーザーごとのフォルダ分け等）
- URLの命名規則
- 画像の有効期限管理（ライフサイクルルール）

## 質問
1. boto3 vs httpx/requests直接: R2のS3互換APIを叩くのにboto3が最適か？軽量な代替はあるか？
2. r2.dev URLとカスタムドメイン: テスト段階ではr2.devで十分か？
3. ライフサイクルルール: R2側で自動削除を設定すべきか、スクリプト側で削除すべきか？
4. エラーハンドリング: R2アップロード失敗時のフォールバック（lh3に戻す等）
5. セキュリティ: バケットをパブリックにする際のリスクと対策

## 期待する成果物
1. R2統合のための具体的なコード変更（diff形式）
2. Cloudflare R2のセットアップ手順書
3. 必要な環境変数一覧
4. GitHub Secrets設定手順
5. テスト手順

## 参照ファイル
- ig_auto_poster.py（現在のスクリプト）
- .github/workflows/auto_post.yml（GitHub Actionsワークフロー）
- docs/codex_briefing.md（プロジェクト全体の情報）
- docs/auto_poster_design.md（設計書）
