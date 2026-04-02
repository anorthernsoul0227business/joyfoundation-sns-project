# Codex壁打ち指示書: SNS完全自動投稿システム構築

## あなたへの依頼

SNS完全自動投稿システムを構築してください。Google Sheetsに投稿内容と日時を登録すると、GitHub Actionsで定期実行されるスクリプトがX（Twitter）とInstagramに自動投稿するシステムです。将来的にはカレンダーUIを持つWebアプリに発展させ、最終的には一般向けにアプリとしてリリースすることを見据えた設計にしてください。

---

## 現在の環境・資産

### リポジトリ

**メインプロジェクト（コンテンツ管理）:**
- GitHub: `anorthernsoul0227business/joyfoundation-sns-project`
- ローカル: `/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project`
- 言語: Python（既存スクリプト多数）

**自動投稿リポジトリ（既存・TypeScript版）:**
- GitHub: `anorthernsoul0227business/sns-auto-poster`
- ローカル: `/Users/kitakoujirou/Desktop/AI関連/sns-auto-poster`
- 言語: TypeScript (Node.js 20)
- 状態: GitHub Actions設定済みだが**Run failedの状態**
- 構成: YAMLファイルベースの投稿管理（content/posts/YYYY-MM/*.yaml）
- ワークフロー: 毎時0分にcron実行、Node.jsビルド→実行
- プラットフォーム対応: Twitter, Instagram, LINE（各poster実装あり）

### API・認証情報

| API | 状態 | 詳細 |
|-----|------|------|
| X (Twitter) API | セットアップ済み | OAuth1.0a認証。**ただし現在Read権限のみで投稿が403エラー。Developer PortalでRead/Write権限に変更し、Access Tokenを再生成する必要がある** |
| Google Sheets API | 動作確認済み | サービスアカウント: `sheets-api-service@gmailsendapp-478003.iam.gserviceaccount.com`、認証JSON: `~/.config/gspread/service_account.json` |
| Google Drive API | 動作確認済み | 同上のサービスアカウント。画像フォルダへの読み書き権限あり |
| Instagram Graph API | **未設定** | FBページ管理者権限が未取得（FBアカウント審査中）。IGビジネスアカウント `@harmonicscience_jp` は存在 |
| LINE API | 未設定 | ログイン情報確認待ち |

### 認証キーの格納場所
- ローカル: `/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/.env`
  ```
  OPENAI_API_KEY=xxx
  X_CONSUMER_KEY=xxx
  X_CONSUMER_SECRET=xxx
  X_ACCESS_TOKEN=xxx
  X_ACCESS_TOKEN_SECRET=xxx
  ```
- `.gitignore` に `.env` を設定済み

### Google Sheets（投稿管理）

**スプレッドシートID:** `1yv9-rnytRH6jEzzFeNHye0T1JnR4aQvr0bryZUJr7iM`

**シート1: X投稿v2（X/Twitter用）**
| 列 | ヘッダー | 説明 |
|----|---------|------|
| A | Day | 投稿Day番号（Day1, Day2...）またはイベント名 |
| B | 投稿タイプ | 豆知識型/体験共有型/イベント告知 等 |
| C | 投稿テキスト | ツイート本文 |
| D | 画像 | IMAGE()数式でプレビュー表示（自動） |
| E | 画像リンク | Google DriveのURL |
| F | 画像2 | IMAGE()数式（自動） |
| G | 画像リンク2 | Google DriveのURL |
| H | 画像3 | IMAGE()数式（自動） |
| I | 画像リンク3 | Google DriveのURL |
| J | リプ投稿（リンク・補足） | スレッド用テキスト |
| K | Xカウント | 文字数 |
| L | 投稿時間 | `20:00-22:00` 等（**要フォーマット統一: YYYY-MM-DD HH:MM**） |
| M | ステータス | 下書き / 投稿予約 / 投稿済み / 投稿失敗 |
| N | 確認 | 人間の確認チェック |
| O | メモ | 投稿結果等の自動記録 |

現在のデータ: 18行（固定ツイート + Day1-5 + イベント告知12件）
投稿済み: Row3(Day1), Row4(Day2), Row9(太陽食品コラボ)

**シート2: Instagram**
| 列 | ヘッダー | 説明 |
|----|---------|------|
| A | No | 連番 |
| B | カテゴリ | 基礎知識 等 |
| C | タイトル | 投稿タイトル |
| D | キャプション | IG投稿文（ハッシュタグ含む） |
| E | 形式 | カルーセル5枚 / 単画像 等 |
| F | 画像 | IMAGE()数式（自動） |
| G | 画像リンク | Google DriveのURL |
| H | 画像2 | IMAGE()数式（自動） |
| I | 画像リンク2 | URL |
| J | 画像3 | IMAGE()数式（自動） |
| K | 画像リンク3 | URL |
| L | ステータス | 下書き / 投稿予約 / 投稿済み / 投稿失敗 |
| M | 予定日 | 投稿予定日 |
| N | 確認 | 確認チェック |
| O | メモ | 備考 |

投稿済み: Row2(Day1), Row3(Day2)

### Google Drive画像フォルダ

**フォルダID:** `1vPODCZ9ZdnGtpnUBRkvvmePs21WGbF9i`
**フォルダ名:** HSC_SNS用画像フォルダ
**共有設定:** 
- keiichiro.kita@gmail.com（オーナー）
- a.northern.soul.0227@gmail.com（編集者）
- sheets-api-service@gmailsendapp-478003.iam.gserviceaccount.com（編集者）
- リンクを知っている全員（閲覧者）

**フォルダ構成:**
```
HSC_SNS用画像フォルダ/
├── ★2026.3.1 画像 1/
│   ├── サウンドヒーリングSNS画像/（Day別投稿用画像27枚）
│   ├── サウンドヒーリング実技を学ぶ/（研修写真30枚+サブフォルダ）
│   ├── 自然景色、室内関係/（風景写真多数）
│   ├── 2025 Holistic VeganCruise 画像/
│   ├── Ipad 画像/
│   └── Miami ZOO/
├── 01_ロゴ・バナー/（11枚）
├── 02_スターライトヒーリング/（10枚）
├── 03_体感音響・ワークショップ/（15枚）
├── 04_イベント（太陽食品・ここちよい音の日）/（6枚）
├── 05_メディア掲載/（1枚）
├── 06_カルーセル素材/（6枚）
├── 07_Instagram下書き画像/（2枚）
├── 08_学会・学術/（2枚）
├── 09_CDジャケット・書籍表紙/（1枚）
├── Miami ZOO/
└── SNS投稿管理シート（ショートカット）
```

### 既存Pythonスクリプト（メインプロジェクト内）

**重要なもの:**
- `x_auto_poster.py` - スプレッドシート連携X自動投稿（作成済み、テスト未実施）
  - シートから「投稿予約」ステータスの行を読み取り
  - 投稿時間が過ぎていれば投稿実行
  - Drive画像をDL→X APIにアップロード→投稿
  - 投稿後にステータスを「投稿済み」に更新
- `post_x.py` - X投稿の基本スクリプト（v1.1 + v2 APIフォールバック）
- `x_scheduler.py` - JSONベースのスケジューラー（CLIツール）

### 既存TypeScriptシステム（sns-auto-posterリポジトリ）

```
sns-auto-poster/
├── .github/workflows/scheduled-post.yml  ← 毎時cron実行
├── src/
│   ├── index.ts          ← メインエントリー
│   ├── config.ts         ← 環境変数管理
│   ├── platforms/
│   │   ├── twitter.ts    ← X投稿ロジック
│   │   ├── instagram.ts  ← IG投稿ロジック
│   │   └── line.ts       ← LINE投稿ロジック
│   ├── scheduler/
│   │   └── cron-handler.ts ← YAML読み込み+投稿判定
│   └── utils/
│       └── logger.ts
├── content/posts/         ← YYYY-MM/xxx.yaml形式の投稿データ
│   ├── 2026-03/（X投稿29件 + IG投稿13件）
│   ├── 2026-04/（X投稿20件）
│   └── 2026-05/（X投稿31件）
├── dist/                  ← TypeScriptビルド済み
├── package.json           ← Node.js 20, tsx, vitest, wrangler対応
└── tsconfig.json
```

**GitHub Actions ワークフロー（既存）:**
```yaml
name: Scheduled SNS Post
on:
  schedule:
    - cron: '0 * * * *'  # 毎時0分
  workflow_dispatch:
jobs:
  post:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run build && npm start
        env:
          TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
          TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
          TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
          TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}
          INSTAGRAM_ACCESS_TOKEN: ${{ secrets.INSTAGRAM_ACCESS_TOKEN }}
          INSTAGRAM_BUSINESS_ACCOUNT_ID: ${{ secrets.INSTAGRAM_BUSINESS_ACCOUNT_ID }}
      - name: Commit status updates
        run: |
          git add content/posts/
          git diff --staged --quiet || git commit -m "chore: update post statuses [skip ci]"
          git push
```
**状態: Run failed** - 原因未調査

---

## ユーザー要件

### 最優先（Phase 1）
1. **X + Instagramへの完全自動投稿**
   - Google Sheetsの投稿管理シートに文章・画像リンク・投稿日時を入力
   - ステータスを「投稿予約」にすると、指定時間に自動投稿される
   - 投稿完了後、ステータスが「投稿済み」に自動更新される
   - 画像はGoogle Driveから取得し、プラットフォーム別に自動リサイズ
     - X: 1200×675px (16:9) or 1200×1200px (1:1)
     - IG: 1080×1350px (4:5)
   - 投稿テキスト+画像1〜3枚対応

2. **編集用と投稿用の安全な分離**
   - 「下書き」→「確認済み」→「投稿予約」のステータス遷移
   - スクリプトは「投稿予約」ステータスのみ処理する
   - 「投稿失敗」は自動リトライしない（人間が確認して手動で「投稿予約」に戻す）

3. **低コスト運用**
   - GitHub Actions無料枠（月2,000分）内で運用
   - 追加の有料サービスは使わない

### 次の優先（Phase 2）
4. **カレンダー型管理画面**
   - Googleカレンダーのような見た目
   - 日/週/月の表示切り替え
   - SNSごとの個別カレンダー + 統合カレンダー表示
   - ドラッグ&ドロップで投稿時間を配置・変更
   - 一目で「いつ・どのSNSに・何が投稿されるか」把握できる
   - 過去の投稿をカレンダー上で遡って確認（アーカイブ機能）

### 中長期（Phase 3）
5. Instagramストーリーズ・リール対応
6. YouTube・note等への拡張
7. **アプリ化して一般向けにリリース**

---

## 判断が必要な設計ポイント

### 1. 言語選択: Python vs TypeScript
- **既存資産**: メインプロジェクトはPython、sns-auto-posterはTypeScript
- **Python版（x_auto_poster.py）**: 動作確認済み、gspreadでSheets連携簡単、Pillowで画像処理
- **TypeScript版（sns-auto-poster）**: GitHub Actions設定済みだがfailed状態、YAMLベース
- **質問**: どちらをベースにするか？ または新規で作り直すか？

### 2. データソース: Google Sheets vs YAMLファイル
- **現在のSheets**: 圭一郎さん（クライアント）と共有済み、ブラウザから編集可能
- **現在のYAML**: リポジトリ内に90件の投稿データあり、gitで管理
- **質問**: Sheetsをマスターデータとするか？両方対応するか？

### 3. Instagram画像URL問題
- IG Graph APIは**公開HTTPS URL**が必須
- Google Driveのプライベートリンクは使えない
- **候補**:
  - A: `https://lh3.googleusercontent.com/d/{file_id}` 形式（Driveの公開リンク）
  - B: GitHub Pagesに一時アップロード
  - C: Cloudflare R2等の外部ストレージ
  - D: imgBB等の無料画像ホスティングAPI

### 4. cron精度
- GitHub Actionsのcronは±15分のズレあり
- 投稿時間の厳密さをどこまで求めるか
- 推奨: スクリプト側で「予約時刻が過去 かつ 24時間以内」の投稿を処理

### 5. Instagram API準備状況
- FBアカウント（keiichiro.kita@gmail.com）が審査中
- 審査が通らない場合の代替手段の検討が必要
- Meta Developer AppとApp Reviewの申請手順

### 6. X API権限修正
- 現在Read権限のみ → Read/Write権限に変更必要
- Developer Portalでの操作手順とAccess Token再生成

---

## 成果物として期待するもの

1. **実装可能な技術設計書**（アーキテクチャ図、ファイル構成、データフロー）
2. **Phase 1の実装計画**（具体的なステップ、ファイル単位のタスク分解）
3. **判断ポイントへの推奨案**（根拠付き）
4. **Phase 2カレンダーUIの設計案**（技術スタック、コンポーネント設計）
5. **リスクと制約の整理**

---

## 参考: 調査済みのツール・手法

NotebookLMで調査した10本のYouTube動画から得た知見:

| # | 手法 | ツール | 適合度 |
|---|------|--------|--------|
| 1 | Claude Code + MCP + Buffer | AIが戦略的に自律判断して投稿 | 将来的に有望 |
| 2 | n8n + OpenAI + Drive監視 | 完全自動ループ | 高コスト |
| 3 | GASラボツール(GAS+スプシ) | IGリール予約投稿 | IG対応に有用 |
| 4 | GAS + スプシ + X API | スプシから直接X投稿 | **最も親和性高い** |
| 5 | Make.com + Claude + DALL-E | ノーコードIG自動投稿 | 月3,000円 |
| 6 | しんたろ。ツール(GAS多機能) | X予約1万件対応 | UI参考に |
| 7 | スプシ + Make + Buffer | 投稿ストック→シャッフル配信 | 参考程度 |
| 8 | Manus(AIエージェント) | IG全自動（調査→投稿） | IG権限回避の可能性 |
| 10 | Notion + Claude + Claude Code | 日記から投稿ネタ自動抽出 | 将来構想 |

---

## 補足: Xアカウント情報
- アカウント: @SFH_Science
- URL: https://x.com/SFH_Science
- 用途: 日常Tips・イベント告知・記事シェア
- X Developer Portal: セットアップ済み（$5クレジット購入済み）

## 補足: Instagramアカウント情報
- アカウント: @harmonicscience_jp
- アカウント種別: ビジネスアカウント
- 用途: カルーセル・リール・ストーリーズ
- FBページ紐付け: 未完了（旧ページharmonicscience は管理者権限喪失）
