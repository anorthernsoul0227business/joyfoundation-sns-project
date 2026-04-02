# SNS完全自動投稿システム 技術設計書

> 作成日: 2026-04-02
> プロジェクト: サウンドヒーリング協会 SNS運用
> リポジトリ: anorthernsoul0227business/sns-auto-poster

---

## ユーザー要件（音声ソースより）

### 最優先
- X + Instagram に完全自動投稿（シートに文章・画像を配置→指定時間に自動投稿）
- 編集用シートと投稿完了シートの分離（編集中のものは投稿されない）
- 画像の自動リサイズ（プラットフォーム別に比率を自動調整）

### 次に実装
- カレンダー型管理画面（Googleカレンダーのような形式）
  - 日単位・週単位の表示切り替え
  - SNSごと/統合カレンダーの切り替え
  - ドラッグ&ドロップで投稿時間を配置・変更
  - 一目で「いつ・どのSNS・何が投稿されるか」把握できる
- アーカイブ機能（過去の投稿をカレンダーで遡って確認）

### 中長期
- Instagramストーリーズ・リール対応
- YouTube・note等への拡張
- アプリ化してリリース（一般向けSNS管理ツールとして）

### 技術的な希望
- 低コスト運用: GitHub Actions / Cloudflare の無料枠を活用
- 拡張性: アプリ化を見据えた設計

---

## アーキテクチャ（推奨: ハイブリッド構成）

```
[フロントエンド] Next.js + FullCalendar.js（Phase 2）
    ↓ 読み書き
[データストア] Google Sheets（投稿管理）
    ↑ 定期読み取り
[バックエンド] GitHub Actions (cron)
    ↓ 投稿実行
[API] X API / Instagram Graph API
    ↑ 画像取得+リサイズ
[ストレージ] Google Drive（画像保管）
```

---

## 1. GitHub Actions ワークフロー設計

### ワークフロー定義

```yaml
# .github/workflows/auto_post.yml
name: SNS Auto Poster

on:
  schedule:
    - cron: '0 0 * * *'    # JST 09:00
    - cron: '0 3 * * *'    # JST 12:00
    - cron: '0 9 * * *'    # JST 18:00
    - cron: '0 11 * * *'   # JST 20:00
    - cron: '0 12 * * *'   # JST 21:00
    - cron: '0 13 * * *'   # JST 22:00
  workflow_dispatch:

env:
  TZ: Asia/Tokyo

jobs:
  post:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - name: Setup Google credentials
        run: |
          mkdir -p ~/.config/gspread
          echo '${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}' > ~/.config/gspread/service_account.json
      - name: Run auto poster
        env:
          X_CONSUMER_KEY: ${{ secrets.X_CONSUMER_KEY }}
          X_CONSUMER_SECRET: ${{ secrets.X_CONSUMER_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_TOKEN_SECRET: ${{ secrets.X_ACCESS_TOKEN_SECRET }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          IG_BUSINESS_ACCOUNT_ID: ${{ secrets.IG_BUSINESS_ACCOUNT_ID }}
        run: python sns_auto_poster.py
```

### cron精度対策
- GitHub Actionsのcronは±15分のズレあり
- スクリプト側で「予約時刻が過去 かつ 24時間以内」の投稿を処理する設計
- 未来の投稿はスキップ、24時間以上前の投稿も安全のためスキップ

### Secrets管理

| Secret名 | 内容 |
|-----------|------|
| X_CONSUMER_KEY | X API Consumer Key |
| X_CONSUMER_SECRET | X API Consumer Secret |
| X_ACCESS_TOKEN | X API Access Token |
| X_ACCESS_TOKEN_SECRET | X API Access Token Secret |
| GOOGLE_SERVICE_ACCOUNT_JSON | サービスアカウントJSON全文 |
| IG_ACCESS_TOKEN | Instagram Long-lived Token |
| IG_BUSINESS_ACCOUNT_ID | IGビジネスアカウントID |

### エラーハンドリング
- 指数バックオフ付きリトライ（最大3回）
- 429(レート制限): Retry-Afterヘッダー待機
- 401/403(認証エラー): リトライせず「認証エラー」記録
- 500系(サーバーエラー): バックオフでリトライ
- 重複投稿: スキップ
- 画像エラー: テキストのみ投稿を試行

---

## 2. 統合投稿スクリプト設計

### ファイル構成

```
sns-auto-poster/
├── sns_auto_poster.py   # メインエントリーポイント
├── config.py            # 定数・環境変数管理
├── sheet_manager.py     # Google Sheets読み書き
├── image_handler.py     # Drive画像取得・リサイズ
├── x_poster.py          # X投稿ロジック
├── ig_poster.py         # Instagram投稿ロジック
├── notifier.py          # 通知ロジック
├── requirements.txt
└── .github/workflows/auto_post.yml
```

### 投稿フロー

```
1. GitHub Actions cron起動
2. sheet_manager: スプシから「投稿予約」ステータスの行を取得
3. 投稿時間チェック（過去 かつ 24時間以内）
4. image_handler: Drive画像DL → プラットフォーム別リサイズ
5. x_poster / ig_poster: API経由で投稿
6. sheet_manager: ステータスを「投稿済み」に更新、投稿IDを記録
7. notifier: 結果をログ/通知
```

---

## 3. Instagram Graph API

### 要件
- IGビジネスアカウント（@harmonicscience_jp: 完了）
- FBページ管理者権限（審査中）
- Meta Developer App（未作成）
- instagram_content_publish権限（審査必須）

### Container方式投稿フロー
1. `POST /{ig-user-id}/media` でコンテナ作成（画像URL+キャプション）
2. ステータスポーリング（FINISHED待ち）
3. `POST /{ig-user-id}/media_publish` で公開

### 画像URL問題
- IG Graph APIは公開HTTPS URLが必須
- Google Driveプライベートリンクは不可
- 解決策: `https://lh3.googleusercontent.com/d/{file_id}` 形式を使用

### Long-lived Token自動更新
- 有効期限60日
- GitHub Actions で月2回自動更新（毎月1日・15日）

---

## 4. シート設計

### ステータス遷移
```
下書き → 確認済み → 投稿予約 → 投稿済み
                              → 投稿失敗（手動で「投稿予約」に戻してリトライ）
```

### 投稿日時フォーマット
- 統一: `YYYY-MM-DD HH:MM`（例: 2026-04-03 20:00）

### エラーリカバリー
- 「投稿失敗」は自動リトライしない（安全策）
- 人間がメモ列のエラー内容を確認→原因修正→手動で「投稿予約」に戻す

---

## 5. 画像自動リサイズ

### プラットフォーム別サイズ

| プラットフォーム | サイズ | 比率 | 最大サイズ |
|----------------|--------|------|-----------|
| X（横長） | 1200×675px | 16:9 | 5MB |
| X（正方形） | 1200×1200px | 1:1 | 5MB |
| IG（フィード） | 1080×1350px | 4:5 | 8MB |
| IG（正方形） | 1080×1080px | 1:1 | 8MB |
| IG（ストーリー） | 1080×1920px | 9:16 | - |

### リサイズ方式
- **pad**: アスペクト比維持+余白パディング（データ図表・ロゴ向き）
- **crop**: アスペクト比維持+はみ出しクロップ（風景・人物写真向き）
- 自動判定: 元画像とターゲットの比率差で選択

### ファイルサイズ制限対応
- JPEG品質を95→60まで段階的に下げて制限内に収める

---

## 6. Phase 2: カレンダーUI

### 技術スタック
- Next.js 14 + FullCalendar.js v6 + Tailwind CSS
- Google Sheets API双方向連携
- NextAuth.js（Googleアカウント認証、ホワイトリスト制御）
- Vercel無料デプロイ

### 機能
- 月/週表示切り替え
- SNSごとの色分け（X=青, IG=ピンク）
- ドラッグ&ドロップで投稿時間変更
- クリックで投稿詳細/編集モーダル
- 投稿済みアーカイブ表示

---

## コスト見積もり

| 項目 | コスト |
|------|--------|
| GitHub Actions | 無料（月2,000分） |
| X API Free tier | 無料（月1,500ツイート） |
| Instagram Graph API | 無料 |
| Google Sheets/Drive API | 無料 |
| Vercel（カレンダーUI） | 無料枠 |
| **合計** | **$0/月** |

---

## 実装ロードマップ

### Phase 1A: X自動投稿の本番稼働（1-2日）
1. X API権限修正（Read→Read/Write）
2. GitHubリポジトリにスクリプト+ワークフローpush
3. GitHub Secretsに認証情報設定
4. dry-runテスト→本番稼働

### Phase 1B: 画像リサイズ対応（1日）
1. image_handler.py実装
2. 投稿スクリプトに統合
3. テスト確認

### Phase 1C: Instagram API準備（FBページ権限待ち）
1. FBページ管理者権限取得
2. Meta Developer App作成
3. instagram_content_publish審査
4. Long-lived Token取得
5. ig_poster.pyテスト

### Phase 2: カレンダーUI（1-2週間）
1. Next.jsプロジェクト初期化
2. FullCalendar統合
3. Google Sheets API連携
4. Vercelデプロイ
