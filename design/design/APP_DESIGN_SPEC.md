# SNS Calendar App — 設計仕様書 v0.1

**作成日**: 2026-04-16
**ステータス**: Draft（Codex壁打ち前）

---

## 1. プロダクトビジョン

### 1.1 一言で

> カレンダーにドラッグするだけで、複数SNSに自動投稿できるアプリ

### 1.2 ミッション

ネットに疎い世代の事業者でも、プロのインフルエンサーと同じレベルのSNS運用ができるツールを提供する。

### 1.3 差別化ポイント

| 競合 | 弱み | 本アプリの強み |
|---|---|---|
| Buffer / Later | 英語UI・LINE/note非対応 | 日本語ネイティブ・LINE/note対応 |
| Hootsuite | 高額($99/月)・複雑 | 低コスト・シンプルモードあり |
| Planoly | Instagram特化 | マルチプラットフォーム |
| 国内ツール | 分析特化で投稿管理弱い | カレンダー型投稿管理が中心機能 |

### 1.4 市場機会

日本市場において「LINE + note.com + X + Instagram をカレンダーUIで一元管理できるツール」は2026年4月時点で存在しない。

---

## 2. ターゲットユーザー

### 2.1 ペルソナ

#### ペルソナA: 「おじいちゃん事業者」（プライマリ）
- **属性**: 60代男性、地方の中小企業経営者
- **ITスキル**: スマホは使えるがSNSは苦手。LINEは日常利用
- **課題**: 「SNSをやりたいが何をどう投稿すればいいか分からない」
- **求めること**: 迷わない操作、テンプレート、1タップ投稿
- **利用シーン**: スマホからカレンダーを見て「今日の投稿」を確認→1タップで投稿

#### ペルソナB: 「SNS担当者」（セカンダリ）
- **属性**: 30-40代、企業のSNS担当（1人運用）
- **ITスキル**: Instagramは使えるがXやnoteは未経験
- **課題**: 「1つのSNSしかやっていないが、他にも広げたい」
- **求めること**: 1つの記事を複数SNSに同時投稿、承認ワークフロー
- **利用シーン**: PCで下書き作成→上司に確認依頼→承認後に予約投稿

#### ペルソナC: 「インフルエンサー」（パワーユーザー）
- **属性**: 20-30代、フォロワー1万〜10万
- **ITスキル**: 高い。複数ツール併用
- **課題**: 「投稿スケジュールが複雑で管理が大変」
- **求めること**: 詳細なスケジュール管理、分析、一括操作、D&D
- **利用シーン**: 月間カレンダーで全SNSの投稿計画を一覧→D&Dで調整

### 2.2 UIモード

| モード | 対象 | 表示 |
|---|---|---|
| **シンプルモード** | ペルソナA/B | 今日・明日の投稿 + 大きな「投稿する」ボタン |
| **プロモード** | ペルソナC | 月/週/日カレンダー + D&D + 分析 + 一括操作 |

初回起動時に選択。いつでも切替可能。

---

## 3. 機能一覧（MVP → 将来）

### 3.1 Phase 1: MVP（Webアプリ）

| # | 機能 | 詳細 | 優先度 |
|---|---|---|---|
| F-01 | カレンダー表示 | 月/週/日ビュー切替、SNSごとの色分け表示 | P0 |
| F-02 | 投稿作成 | テキスト+画像の投稿を作成。プレビュー付き | P0 |
| F-03 | ドラッグ&ドロップ | 下書きをカレンダーにD&Dで予約 | P0 |
| F-04 | マルチプラットフォーム | X, Instagram に自動投稿 | P0 |
| F-05 | 編集/投稿シート分離 | 編集中の下書き一覧と確定済み投稿キューを分離 | P0 |
| F-06 | 画像自動調整 | プラットフォーム別に画角を自動変換 | P1 |
| F-07 | アーカイブ | 過去投稿をカレンダー上で閲覧 | P1 |
| F-08 | 通知 | 投稿成功/失敗をメールで通知 | P1 |
| F-09 | ユーザー認証 | メール+パスワードログイン | P0 |
| F-10 | SNSアカウント連携 | OAuth経由でX/IGアカウントを接続 | P0 |

### 3.2 Phase 1.5: AI記事生成

| # | 機能 | 詳細 | 優先度 |
|---|---|---|---|
| F-11 | AI下書き生成 | 資料テキスト→投稿テキスト自動生成（Claude API） | P1 |
| F-12 | 資料アップロード | PDF/画像/テキスト/URLからの読み込み・テキスト抽出 | P1 |
| F-13 | 一括カレンダー配置 | 生成結果（N日分×複数SNS）をカレンダーに一括D&D | P1 |
| F-14 | NGルールプリセット | 業種別の表現ルール管理（薬機法、景表法等） | P2 |
| F-15 | トーン・スタイル設定 | やわらかい/ビジネス/カジュアル等の文体切替 | P2 |
| F-16 | 音声→投稿生成 | 音声ファイル→Whisper文字起こし→投稿テキスト化 | P2 |
| F-17 | 画像自動抽出・マッピング | 資料PDF内の画像を抽出し投稿に自動割当 | P2 |

### 3.3 Phase 2: 拡張

| # | 機能 | 詳細 |
|---|---|---|
| F-18 | チーム・承認フロー | 下書き→承認→公開のワークフロー |
| F-19 | YouTube対応 | 動画アップロード+予約公開 |
| F-20 | note対応 | 記事投稿（APIが限定的なため要検討） |
| F-21 | 分析ダッシュボード | フォロワー推移、エンゲージメント |
| F-22 | IGストーリー/リール | ストーリーズ・リール投稿対応 |
| F-23 | テンプレート | 投稿テンプレート（シンプルモード用） |

### 3.4 Phase 3: アプリ化+LINE

| # | 機能 | 詳細 |
|---|---|---|
| F-24 | iOS/Androidアプリ | React Native (Expo) でApp Store公開 |
| F-25 | LINE Messaging API連携 | ステップ配信スケジュール管理 |
| F-26 | プッシュ通知 | 投稿リマインダー、承認リクエスト |
| F-27 | 課金・サブスクリプション | Stripe連携、フリー/プロ/ビジネスプラン |

---

## 4. 画面設計

### 4.1 画面一覧

```
┌─ 認証系
│  ├─ ログイン画面
│  ├─ サインアップ画面
│  └─ パスワードリセット
│
├─ メイン（シンプルモード）
│  ├─ ホーム（今日の投稿）
│  ├─ 投稿作成（ウィザード形式）
│  └─ 設定
│
├─ メイン（プロモード）
│  ├─ ダッシュボード
│  ├─ カレンダー（月/週/日）
│  ├─ 下書き一覧
│  ├─ 投稿作成・編集
│  ├─ AI記事生成（資料→投稿）
│  ├─ メディアライブラリ
│  ├─ アーカイブ
│  ├─ 分析（Phase 2）
│  └─ 設定
│
└─ 共通
   ├─ SNSアカウント連携
   ├─ 通知設定
   └─ プラン・課金（Phase 3）
```

### 4.2 カレンダー画面（プロモード・コア画面）

```
┌──────────────────────────────────────────────────────┐
│  ← 2026年4月 →        [月] [週] [日]   🔍  ⚙️      │
│                                                       │
│  SNSフィルター: [X ✓] [IG ✓] [YT ○] [note ○]       │
│                                                       │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐        │
│  │ 月   │ 火   │ 水   │ 木   │ 金   │ 土   │ 日   │  │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤        │
│  │ 14  │ 15  │ 16  │ 17  │ 18  │ 19  │ 20  │        │
│  │     │     │🔵18:│🔴08:│🔵20:│🔴12:│🔵08:│        │
│  │     │     │科学 │豆知 │呼吸 │文化 │Tips │        │
│  │     │     │🟢12:│🟢18:│🟢12:│🟢18:│🟢12:│        │
│  │     │     │IG科 │IG豆 │IG呼 │IG文 │IGTi │        │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤        │
│  │ 21  │ 22  │ 23  │ 24  │ 25  │ 26  │ 27  │        │
│  │🔵18:│🔵20:│🔵12:│🔵18:│🔵08:│🔵12:│🔵20:│        │
│  │理念 │名言 │科学 │体験 │40代 │WHO  │Tips │        │
│  │🟢10:│🟢18:│🟢12:│🟢18:│🟢10:│🟢18:│🟢12:│        │
│  │IG理 │IG名 │IG科 │IG体 │IG40 │IGWH │IGTi │        │
│  └─────┴─────┴─────┴─────┴─────┴─────┴─────┘        │
│                                                       │
│  凡例: 🔵X  🟢IG  🔴YouTube  🟡note                  │
│                                                       │
│  ┌─ 下書きパネル（サイドバー）──────────────────┐     │
│  │ 📝 下書き (5件)                              │     │
│  │ ┌────────────────────────────────┐           │     │
│  │ │ ≡ 体感音響の科学           🔵🟢│ ← D&D    │     │
│  │ └────────────────────────────────┘           │     │
│  │ ┌────────────────────────────────┐           │     │
│  │ │ ≡ 自然音の選び方           🔵  │ ← D&D    │     │
│  │ └────────────────────────────────┘           │     │
│  └──────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

**操作フロー:**
1. サイドバーの下書きカードを掴む（ドラッグ開始）
2. カレンダー上の日付・時間位置にドロップ
3. ドロップ時にダイアログ: 投稿時間の確定 + 対象SNS選択
4. 確定 → カレンダーに表示 + 投稿キューに追加

### 4.3 ホーム画面（シンプルモード）

```
┌──────────────────────────────────┐
│  🏠 こんにちは、圭一郎さん        │
│                                   │
│  ─── 今日の投稿 ──────────       │
│                                   │
│  ┌─────────────────────────┐     │
│  │ 🔵 X  18:00              │     │
│  │                           │     │
│  │ 「音は心の糧である」       │     │
│  │  ── 喜田圭一郎            │     │
│  │                           │     │
│  │ [プレビュー] [✏️編集]      │     │
│  │                           │     │
│  │  ●━━━━━━━━○ 予約済み     │     │
│  └─────────────────────────┘     │
│                                   │
│  ┌─────────────────────────┐     │
│  │ 🟢 IG  20:00             │     │
│  │                           │     │
│  │ 【音の高さで体の反応が...】 │     │
│  │ [画像プレビュー]           │     │
│  │                           │     │
│  │ [プレビュー] [✏️編集]      │     │
│  │                           │     │
│  │  ●━━━━━━━━○ 予約済み     │     │
│  └─────────────────────────┘     │
│                                   │
│  ─── 明日の投稿 (2件) ─────     │
│  ...                              │
│                                   │
│  ┌─────────────────────────────┐ │
│  │   ＋ 新しい投稿を作る        │ │
│  └─────────────────────────────┘ │
│                                   │
│ [🏠ホーム] [📝作成] [📅カレンダー] [⚙設定] │
└──────────────────────────────────┘
```

### 4.4 投稿作成画面

```
┌──────────────────────────────────────────┐
│  ← 投稿を作成                   [下書き保存] │
│                                           │
│  投稿先: [X ✓] [IG ✓] [YT ○] [note ○]  │
│                                           │
│  ┌─ テキスト ────────────────────────┐   │
│  │                                    │   │
│  │ ここにテキストを入力...             │   │
│  │                                    │   │
│  │                                    │   │
│  └────────────────────────────────────┘   │
│  X: 0/280  IG: 制限なし                    │
│                                           │
│  ┌─ 画像 ─────────────────────────────┐  │
│  │  [＋ 画像を追加]                    │  │
│  │  ┌────┐ ┌────┐ ┌────┐             │  │
│  │  │img1│ │img2│ │img3│             │  │
│  │  └────┘ └────┘ └────┘             │  │
│  └────────────────────────────────────┘  │
│                                           │
│  ┌─ プレビュー ───────────────────────┐  │
│  │  [X] [IG]  ← タブ切替              │  │
│  │  ┌──────────────────┐              │  │
│  │  │  X風プレビュー    │              │  │
│  │  │  @SFH_Science     │              │  │
│  │  │  テキスト...       │              │  │
│  │  │  [画像]           │              │  │
│  │  └──────────────────┘              │  │
│  └────────────────────────────────────┘  │
│                                           │
│  ┌─ スケジュール ────────────────────┐   │
│  │  ○ 今すぐ投稿                      │   │
│  │  ● 日時を指定: [2026/04/20] [18:00]│   │
│  │  ○ 下書きに保存                    │   │
│  └────────────────────────────────────┘   │
│                                           │
│  [キャンセル]              [予約する 📅]   │
└──────────────────────────────────────────┘
```

### 4.5 AI記事生成画面

```
┌──────────────────────────────────────────────────────┐
│  ← AI記事生成                              [ヘルプ]   │
│                                                       │
│  ┌─ Step 1: 資料をアップロード ───────────────────┐  │
│  │                                                 │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐│  │
│  │  │📄PDF ││📷画像││📝文章 ││🔗URL ││🎤音声 ││  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘│  │
│  │                                                 │  │
│  │  📎 カンガルーカップ2026_開催要項.pdf    ✕     │  │
│  │  📎 公式ポスター.pdf                     ✕     │  │
│  │  📎 圭一郎さん音声メモ_0402.m4a          ✕     │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  ┌─ Step 2: 生成設定 ─────────────────────────────┐  │
│  │                                                 │  │
│  │  投稿先     [X ✓] [IG ✓] [YT ○] [note ○]    │  │
│  │  生成日数   [14日分 ▼]                          │  │
│  │  開始日     [2026/04/20]                        │  │
│  │  投稿時間帯 [朝8-10時 / 夕18-20時 ▼]           │  │
│  │                                                 │  │
│  │  トーン     [やわらかい ▼]                      │  │
│  │             やわらかい / ビジネス / カジュアル   │  │
│  │                                                 │  │
│  │  NGルール   [✓] 効果断言禁止（薬機法対応）     │  │
│  │             [✓] 改行前句読点なし                │  │
│  │             [✓] #KITAサウンドヒーリング 固定    │  │
│  │             [ ] カスタムルールを追加...          │  │
│  │                                                 │  │
│  │  追加指示（任意）                                │  │
│  │  ┌──────────────────────────────────────────┐  │  │
│  │  │ 例: イベント告知は含めず知識系のみ        │  │  │
│  │  └──────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│           [✨ 下書きを生成する]                        │
│                                                       │
│  ┌─ Step 3: 生成結果 ─────────────────────────────┐  │
│  │                                                 │  │
│  │  ✅ 14日分 × 2プラットフォーム = 28件 生成完了  │  │
│  │                                                 │  │
│  │  日付     │ X (文字数)      │ IG (文字数)      │  │
│  │  ─────────┼─────────────────┼─────────────────│  │
│  │  4/20(日) │ 低音と高音 178  │ 音の高さ 285     │  │
│  │  4/21(月) │ 呼吸法   195   │ セルフケア 310   │  │
│  │  4/22(火) │ 虫の声   190   │ 日本の感性 292   │  │
│  │  ...      │ ...             │ ...              │  │
│  │                                                 │  │
│  │  [各行クリックで内容プレビュー・個別編集]        │  │
│  │                                                 │  │
│  │  ┌──────────────────────────────────────────┐  │  │
│  │  │ 🔵X  4/20 18:00                          │  │  │
│  │  │ 低い音 → 体に共鳴しゆるむ                 │  │  │
│  │  │ 高い音 → 意識がクリアに                   │  │  │
│  │  │ ...                      [✏️ 編集] [🗑]  │  │  │
│  │  └──────────────────────────────────────────┘  │  │
│  │                                                 │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  [全て下書きに保存]  [📅 カレンダーに一括配置]        │
└──────────────────────────────────────────────────────┘
```

**操作フロー:**
1. 資料（PDF/音声/テキスト/URL）をアップロード
2. 生成設定（投稿先、日数、トーン、NGルール）を選択
3. 「下書きを生成」→ AI がバックグラウンドで処理（10-30秒）
4. 生成結果を一覧で確認、個別に編集可能
5. 「カレンダーに一括配置」→ カレンダー画面に遷移、全件が配置される

---

## 5. データモデル

### 5.1 ER図（テキスト表現）

```
User
├── id (uuid, PK)
├── email (unique)
├── password_hash
├── display_name
├── ui_mode ('simple' | 'pro')
├── created_at
└── updated_at

SnsAccount
├── id (uuid, PK)
├── user_id (FK → User)
├── platform ('x' | 'instagram' | 'youtube' | 'note' | 'line')
├── platform_user_id
├── platform_username
├── access_token (encrypted)
├── refresh_token (encrypted)
├── token_expires_at
├── created_at
└── updated_at

Post
├── id (uuid, PK)
├── user_id (FK → User)
├── status ('draft' | 'scheduled' | 'publishing' | 'published' | 'failed')
├── text
├── scheduled_at (nullable)
├── published_at (nullable)
├── created_at
└── updated_at

PostTarget
├── id (uuid, PK)
├── post_id (FK → Post)
├── sns_account_id (FK → SnsAccount)
├── platform_post_id (nullable, 投稿後にセット)
├── platform_post_url (nullable)
├── status ('pending' | 'published' | 'failed')
├── error_message (nullable)
├── published_at (nullable)
└── created_at

PostMedia
├── id (uuid, PK)
├── post_id (FK → Post)
├── sort_order (int)
├── original_url (R2/S3 URL)
├── media_type ('image' | 'video')
├── width (int)
├── height (int)
├── file_size (int)
└── created_at

Notification
├── id (uuid, PK)
├── user_id (FK → User)
├── type ('post_success' | 'post_failure' | 'approval_request')
├── title
├── body
├── post_id (FK → Post, nullable)
├── read (boolean)
├── created_at
└── read_at

GenerationJob (AI記事生成ジョブ)
├── id (uuid, PK)
├── user_id (FK → User)
├── status ('processing' | 'completed' | 'failed')
├── target_platforms (jsonb, ['x', 'instagram'])
├── num_days (int)
├── start_date (date)
├── tone ('soft' | 'business' | 'casual')
├── ng_rules (jsonb, ルール配列)
├── additional_instructions (text, nullable)
├── created_at
└── completed_at

GenerationSource (アップロード資料)
├── id (uuid, PK)
├── job_id (FK → GenerationJob)
├── source_type ('pdf' | 'image' | 'text' | 'url' | 'audio')
├── file_url (R2 URL, nullable)
├── raw_url (外部URL, nullable)
├── extracted_text (text, 抽出済みテキスト)
├── file_name
├── file_size (int)
└── created_at

NgRulePreset (NGルールプリセット)
├── id (uuid, PK)
├── user_id (FK → User, nullable → null=システムデフォルト)
├── name (例: '薬機法対応')
├── rules (jsonb, ルール配列)
├── is_default (boolean)
├── created_at
└── updated_at
```

### 5.2 リレーション

```
User 1:N SnsAccount
User 1:N Post
Post 1:N PostTarget
Post 1:N PostMedia
PostTarget N:1 SnsAccount
User 1:N Notification
User 1:N GenerationJob
GenerationJob 1:N GenerationSource
GenerationJob 1:N Post (生成された下書き)
User 1:N NgRulePreset
```

---

## 6. API設計

### 6.1 RESTful API エンドポイント

```
# 認証
POST   /api/auth/signup
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh

# ユーザー
GET    /api/users/me
PATCH  /api/users/me

# SNSアカウント
GET    /api/sns-accounts
POST   /api/sns-accounts/connect/:platform   (OAuth開始)
GET    /api/sns-accounts/callback/:platform  (OAuthコールバック)
DELETE /api/sns-accounts/:id

# 投稿
GET    /api/posts                 ?status=draft|scheduled|published
                                  &from=2026-04-01&to=2026-04-30
POST   /api/posts                 (下書き作成)
GET    /api/posts/:id
PATCH  /api/posts/:id             (編集)
DELETE /api/posts/:id

# スケジュール操作（D&D対応）
POST   /api/posts/:id/schedule    { scheduled_at, target_platforms[] }
PATCH  /api/posts/:id/reschedule  { scheduled_at }  ← D&Dで移動時
POST   /api/posts/:id/unschedule  (下書きに戻す)
POST   /api/posts/:id/publish-now (即時投稿)

# メディア
POST   /api/media/upload          (multipart/form-data)
DELETE /api/media/:id

# カレンダー用（集約エンドポイント）
GET    /api/calendar?from=&to=&platforms[]=x&platforms[]=instagram
       → { scheduled: [...], published: [...], drafts_count: N }

# AI記事生成
POST   /api/generate              (ジョブ作成+非同期実行開始)
       body: { sources[], target_platforms[], num_days, start_date,
               tone, ng_rules[], additional_instructions }
GET    /api/generate/:job_id      (ジョブ状態+生成結果)
POST   /api/generate/:job_id/apply (生成結果を下書きとして一括保存)
POST   /api/generate/:job_id/apply-to-calendar
       body: { post_times: { post_id: scheduled_at }[] }

# 資料アップロード
POST   /api/sources/upload        (multipart → R2保存+テキスト抽出)
POST   /api/sources/from-url      { url } → テキスト抽出

# NGルールプリセット
GET    /api/ng-rules              (ユーザー+デフォルト)
POST   /api/ng-rules
PATCH  /api/ng-rules/:id
DELETE /api/ng-rules/:id

# 通知
GET    /api/notifications         ?unread=true
PATCH  /api/notifications/:id/read
```

### 6.2 WebSocket（リアルタイム）

```
ws://api/ws
  → { type: 'post_published', post_id, platform, url }
  → { type: 'post_failed', post_id, platform, error }
  → { type: 'notification', notification_id }
```

---

## 7. 技術スタック

### 7.1 確定スタック

| レイヤー | 技術 | 理由 |
|---|---|---|
| **フロントエンド** | Next.js 15 (App Router) + TypeScript | SSR/SSG、React Native移行時に知識が共通 |
| **UIライブラリ** | Tailwind CSS + shadcn/ui | 高速開発、カスタマイズ容易、日本語対応 |
| **カレンダー** | FullCalendar (React) | 月/週/日ビュー、D&D内蔵、イベントリソース対応 |
| **D&D（カレンダー外）** | dnd-kit | モダン、アクセシブル、メンテナンス活発 |
| **バックエンド** | Python FastAPI | 既存スクリプト資産を活用、高速API |
| **ジョブキュー** | Celery + Redis | 予約投稿の時間実行、リトライ |
| **DB** | PostgreSQL (Supabase) | 認証・Storage・Realtime込み |
| **ファイルストレージ** | Cloudflare R2 | 既存利用中、S3互換、無料枠大きい |
| **認証** | Supabase Auth | メール/パスワード + OAuth + RLS |
| **ホスティング** | Vercel (Frontend) + Railway (Backend) | 無料枠活用、デプロイ容易 |
| **CI/CD** | GitHub Actions | 無料枠、テスト・デプロイ自動化 |

### 7.2 参考OSS

| OSS | 参考にする部分 |
|---|---|
| **Postiz** (Next.js + NestJS) | 全体アーキテクチャ、マルチプラットフォーム設計 |
| **Cal.com** (Next.js) | カレンダーUI/UX、D&D実装パターン |
| **Mixpost** (Laravel + Vue) | メディアライブラリ、投稿プレビュー設計 |

### 7.3 FastAPI vs NestJS の判断

| 項目 | FastAPI (Python) | NestJS (TypeScript) |
|---|---|---|
| 既存資産 | ✅ ig_auto_poster.py, x_auto_poster.py, notifier.py がそのまま使える | ❌ 全て書き直し |
| フロントとの言語統一 | ❌ 別言語 | ✅ TypeScript統一 |
| アプリ化移行 | ○ API層なので影響なし | ○ 同上 |
| エコシステム | ○ AI/ML系に強い | ○ Web系に強い |
| **結論** | **Phase 1はFastAPIで開始**（既存資産活用優先） | Phase 2以降で移行を検討 |

---

## 8. ディレクトリ構成（Phase 1）

```
sns-calendar-app/
├── frontend/                     # Next.js
│   ├── src/
│   │   ├── app/                  # App Router
│   │   │   ├── (auth)/           # 認証系ページ
│   │   │   │   ├── login/
│   │   │   │   └── signup/
│   │   │   ├── (main)/           # メインレイアウト
│   │   │   │   ├── calendar/     # カレンダー画面
│   │   │   │   ├── posts/        # 投稿一覧・作成・編集
│   │   │   │   ├── drafts/       # 下書き一覧
│   │   │   │   ├── media/        # メディアライブラリ
│   │   │   │   ├── settings/     # 設定
│   │   │   │   └── home/         # シンプルモード ホーム
│   │   │   └── api/              # API Routes (BFF)
│   │   ├── components/
│   │   │   ├── calendar/         # カレンダー関連
│   │   │   ├── posts/            # 投稿関連
│   │   │   ├── media/            # メディア関連
│   │   │   ├── layout/           # レイアウト
│   │   │   └── ui/               # shadcn/uiベース
│   │   ├── hooks/                # カスタムフック
│   │   ├── lib/                  # ユーティリティ
│   │   ├── stores/               # Zustand ステート管理
│   │   └── types/                # TypeScript型定義
│   ├── public/
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/                      # FastAPI
│   ├── app/
│   │   ├── main.py               # FastAPIアプリ
│   │   ├── config.py             # 設定
│   │   ├── models/               # SQLAlchemy モデル
│   │   ├── schemas/              # Pydantic スキーマ
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── posts.py
│   │   │   ├── calendar.py
│   │   │   ├── sns_accounts.py
│   │   │   ├── media.py
│   │   │   └── notifications.py
│   │   ├── services/
│   │   │   ├── publisher/        # 投稿実行
│   │   │   │   ├── x_publisher.py      # 既存 x_auto_poster から移植
│   │   │   │   ├── ig_publisher.py     # 既存 ig_auto_poster から移植
│   │   │   │   └── base.py             # 共通インターフェース
│   │   │   ├── ai_generator/    # AI記事生成
│   │   │   │   ├── generator.py        # Claude API呼び出し+プロンプト管理
│   │   │   │   ├── source_extractor.py # PDF/音声/URL→テキスト抽出
│   │   │   │   ├── ng_checker.py       # NGルール適用チェック
│   │   │   │   └── prompts/            # プロンプトテンプレート
│   │   │   │       ├── x_post.txt
│   │   │   │       └── ig_post.txt
│   │   │   ├── scheduler.py     # Celeryタスク定義
│   │   │   ├── notifier.py      # 既存 notifier.py から移植
│   │   │   └── media_processor.py  # 画像自動変換
│   │   ├── core/
│   │   │   ├── security.py       # 認証
│   │   │   └── database.py       # DB接続
│   │   └── tasks/
│   │       └── celery_tasks.py   # 非同期タスク
│   ├── alembic/                  # マイグレーション
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml            # ローカル開発用
├── .github/
│   └── workflows/
│       ├── frontend-ci.yml
│       └── backend-ci.yml
└── README.md
```

---

## 9. 投稿フロー（シーケンス）

### 9.1 予約投稿フロー

```
User → Frontend → Backend API → DB
                                ↓ (scheduled_at到達)
                   Celery Worker → Publisher → X API / IG API
                                ↓
                         Notifier → Gmail → 圭一郎さん
                                ↓
                      DB更新 (status: published)
                                ↓
                   WebSocket → Frontend (リアルタイム更新)
```

### 9.2 D&Dスケジュール変更フロー

```
1. ユーザーがカレンダー上の投稿カードをドラッグ
2. 別の日時位置にドロップ
3. Frontend → PATCH /api/posts/:id/reschedule { scheduled_at: 新日時 }
4. Backend → DB更新 + Celeryタスク再スケジュール
5. Frontend → カレンダー再描画（楽観的更新）
```

---

## 10. セキュリティ

- アクセストークンはDB内で暗号化保存（AES-256-GCM）
- Supabase RLS（Row Level Security）で全テーブルにユーザー単位のアクセス制御
- API認証: JWT (access token: 15分 + refresh token: 7日)
- CORS: フロントエンドドメインのみ許可
- Rate limiting: 投稿API 30req/min、その他 100req/min

---

## 11. 価格プラン（Phase 3想定）

| プラン | 月額 | 内容 |
|---|---|---|
| **フリー** | ¥0 | 1 SNSアカウント、月30投稿、基本カレンダー |
| **プロ** | ¥1,980 | 5 SNSアカウント、無制限投稿、D&D、分析 |
| **ビジネス** | ¥4,980 | 10 SNSアカウント、チーム3名、承認フロー、LINE連携 |
| **エンタープライズ** | 要相談 | 無制限、カスタムAPI、優先サポート |

---

## 12. 開発スケジュール（概算）

| Phase | 期間 | マイルストーン |
|---|---|---|
| Phase 1.0 | 4-6週 | バックエンドAPI + 認証 + DB |
| Phase 1.1 | 4-6週 | カレンダーUI + D&D + 投稿作成 |
| Phase 1.2 | 2-4週 | X/IG自動投稿連携 + 通知 |
| Phase 1.5 | 4-6週 | AI記事生成（資料→投稿）+ NGルール管理 |
| Phase 1.9 | 2週 | テスト + バグ修正 + 内部運用開始 |
| Phase 2 | 8-12週 | チーム機能 + YouTube/note + 分析 |
| Phase 3 | 8-12週 | React Native + App Store + LINE + 課金 |

---

## 13. 設計決定事項（Codex壁打ち結果 2026-04-16）

### 総評
> 事業仮説は妥当。ただし「カレンダーUI」よりも先に、**投稿API制約・ジョブ信頼性・規約準拠**を設計の主戦場にすべき。
> 最初の6ヶ月は「速度優先」で構築し、ロックインは境界設計（抽象化）で緩和する。

### 決定事項

| # | 項目 | 決定 | 要点 |
|---|---|---|---|
| 1 | カレンダー | **FullCalendar + dnd-kit** 維持 | 成熟度・ドキュメント・実績が最も厚い。Premium機能が必要になったらコスト増に注意 |
| 2 | Auth/DB | **Supabase Auth + Postgres (RLS)** で開始 | Auth境界を抽象化しておきロックイン緩和。MVP〜PMFまでの速度を最大化 |
| 3 | ジョブ | **Celery + Redis** 継続 | 既存Python資産再利用が最短。AI前処理も同一基盤に。将来Node中心化するならBullMQへ段階移行 |
| 4 | リポジトリ | **モノレポ** (apps/web, apps/api, packages/*) | API型定義・OpenAPIクライアント・デザインシステム共有が容易。小規模チームでは運用コスト低 |
| 5 | バックエンド | **FastAPI継続** + 境界設計 | 既存スクリプト流用で最短。「投稿実行ドメイン」を独立サービスとして契約固定すれば後でNestJS化も可能 |
| 6 | AI API | **両対応（プロバイダ抽象化）** | 品質・コスト・可用性は時期で変動。BCP（障害時）と価格交渉力を確保。デフォルト1社+フォールバック1社 |
| 7 | プロンプト管理 | **ハイブリッド**: Git管理YAML + DB差分 | 監査性・再現性（Git履歴）と動的変更（DB）を両立。どの投稿がどのprompt_versionかを記録必須 |
| 8 | 画像変換 | **ハイブリッド**: 主要サイズはアップロード時先行生成、最終最適化は投稿直前 | プレビュー高速化 + 投稿先仕様変更への追従を両立 |
| 9 | note.com | **段階対応**: 初期は「下書き補助/コピーモード」、自動投稿はAPI利用可能になるまで限定提供 | スクレイピング/Puppeteerは規約・凍結・App Store審査リスク大 |
| 10 | Web→RN移行準備 | 今から6項目を実施 | BFF/API契約先行、ドメインロジックpackages化、デザイントークン導入、zodスキーマ共有、UTC保存+TZ表示、添付アップロード抽象化 |

### Web→RN 想定コード共有率
- ビジネスロジック/型/バリデーション: **60〜80%**
- UIコンポーネント: **20〜40%**（RN Webでも差分は残る）

### 優先アクション（実行順）
1. ✅ 投稿先ごとの**機能マトリクス**作成 → `PLATFORM_MATRIX.md`
2. ✅ 予約投稿の**信頼性設計** → `RELIABILITY_DESIGN.md`
3. ✅ 認証/権限の**RLS設計レビュー** → `RLS_DESIGN.md`
4. ✅ LLMの**品質評価基盤** → `LLM_EVAL_DESIGN.md`
5. ✅ note連携の**法務/規約確認** → `NOTE_INTEGRATION_DESIGN.md`

### 追加決定事項（Codex壁打ち R3 2026-04-16）

| # | 項目 | 決定 | 要点 |
|---|---|---|---|
| 11 | マルチテナント | **org_id方式をPhase 1から仕込む** | 個人org自動作成 → Phase 2でチーム招待に拡張。後からの追加はマイグレーションコスト大 |
| 12 | RLSポリシー | **org_id + ヘルパー関数（get_user_org_ids等）** | `(SELECT auth.uid())`ラップで99%+のパフォーマンス改善。全テーブルRLS必須 |
| 13 | バックエンドDB操作 | **Celery worker/FastAPIはservice_roleでRLSバイパス** | 投稿実行・トークン操作・通知作成はバックエンド専用 |
| 14 | トークン保護 | **sns_accounts_safeビュー経由のみフロントエンドに公開** | access_token/refresh_tokenはフロントエンドから一切見えない設計 |
| 15 | NGチェック | **3層ハイブリッド（ルールベース→辞書→LLM）** | Layer 1-2で高速・確実にフィルタ、グレーゾーンのみLLM判定 |
| 16 | 品質評価 | **LLM-as-Judge 6軸評価（トーン/正確性/エンゲージメント/文字数/NG/自然さ）** | 投稿あたり~$0.032、月60件で~$5.52 |
| 17 | プロンプトバージョニング | **prompt_versions + eval_logsテーブル** | 全投稿にprompt_version_idを記録、ABテスト基盤 |
| 18 | note.com連携 | **下書き補助+手動投稿（Phase 1）** | 公式API非公開（405ブロック）。非公式API/Selenium完全禁止。RSS連携で投稿済み自動検知 |
| 19 | note社事前確認 | **問い合わせ実施推奨** | 下書き補助モデルの合法性確認 + API公開予定の確認 |

### 追加決定事項（Codex壁打ち R5 2026-04-16 実装計画）

| # | 項目 | 決定 | 要点 |
|---|---|---|---|
| 20 | モノレポツール | **Turborepo + pnpm** | Vercel親和性、キャッシュ性能、2言語対応 |
| 21 | 型安全パイプライン | **OpenAPI自動生成 (@hey-api/openapi-ts)** | Pydantic→TS型自動同期。pre-commitフックで整合性保証 |
| 22 | ローカル開発 | **docker-compose (Redis+Celery) + Supabase CLI** | 本番環境をローカル再現 |
| 23 | カレンダーD&D | **Phase 1: FC公式Draggableのみ** | dnd-kitは必要に応じてPhase 1.5で追加 |
| 24 | Issue管理 | **30 Issue / 4 Sprint / 7-8週間** | クリティカルパス明確化。→ `IMPLEMENTATION_PLAN.md` |
| 25 | MVPコスト | **~$5-15/月** | Railway従量課金のみ。PMF後は~$60-80/月 |

### 未決定（今後検討）
- **音声文字起こし**: Whisper API vs Google Speech-to-Text（Phase 1.5で決定）
- **オフライン対応**: PWA Service Worker の範囲（Phase 3で決定）
- **生成結果のキャッシュ**: 同一資料再生成時の差分管理（Phase 1.5で決定）
- **評価モデル選定**: Claude Sonnet vs GPT-4o（評価データセット構築後に相関検証して決定）
- **自動再生成閾値**: スコア60 vs 50 vs 70（データセット構築後にチューニング）
