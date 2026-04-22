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

### 追加決定事項（UX: シニア配慮 2026-04-17）

| # | 項目 | 決定 | 要点 |
|---|---|---|---|
| 26 | ミニヘルプシステム | **全UI要素に`?`アイコン + Popover（吹き出し）ヘルプを配置** | シニアユーザー（例: 圭一郎さん世代）が迷わず操作できるUX。ボタン/フィールド/設定項目の横に小さな`?`を置き、クリック or hoverで吹き出し表示。ヘルプ文言はi18n対応前提でJSON管理 |
| 27 | ヘルプモード切替 | **グローバルトグルでON/OFF可能（デフォルトON）** | 熟練者は画面をすっきり表示できる。ヘッダー右上に切替スイッチ配置。設定はユーザープロフィールに永続化（`users.ui_preferences.help_mode_enabled`）。OFF時は`?`アイコン非表示 |

### 未決定（今後検討）
- **音声文字起こし**: Whisper API vs Google Speech-to-Text（Phase 1.5で決定） → **2026-04-22 暫定決定: Whisper API（Section 14参照）**
- **オフライン対応**: PWA Service Worker の範囲（Phase 3で決定）
- **生成結果のキャッシュ**: 同一資料再生成時の差分管理（Phase 1.5で決定）
- **評価モデル選定**: Claude Sonnet vs GPT-4o（評価データセット構築後に相関検証して決定）
- **自動再生成閾値**: スコア60 vs 50 vs 70（データセット構築後にチューニング）

---

## 14. 音声入力AI 増分設計 v0.1（追加: 2026-04-22）

### 14.1 目的と位置づけ

既存 F-16「音声→投稿生成」は**バッチ型**（音声ファイルアップロード → Whisper → 下書き生成）を想定。本セクションはその延長として、**リアルタイム口述ブレスト**を追加する。

**背景**: プライマリペルソナA（高齢事業者・代表例として圭一郎さん）はキーボード入力が負担。思いついた瞬間にスマホ/iPad のマイクボタンを押して話すだけで、SNS投稿の下書き3案が生成される体験を MVP に組み込みたい。

**既存機能との関係**:
| 機能 | 種別 | 対象ペルソナ |
|---|---|---|
| F-16 音声→投稿生成 | バッチ型（資料添付） | B/C |
| F-28〜F-32（本増分） | リアルタイム口述型 | **A（プライマリ）** |

両者は同じ Whisper 基盤を共有し、共通の AI Generator パイプラインに合流する。

### 14.2 追加機能

| # | 機能 | 詳細 | 優先度 | Phase |
|---|---|---|---|---|
| F-28 | マイクボタン音声入力 | 画面下部固定マイクボタン。長押し or タップで録音開始・終了 | P1 | 1.5 |
| F-29 | リアルタイム音声ブレスト | 口述 → Whisper → LLMで X/IG/note の3案を並列生成 | P1 | 1.5 |
| F-30 | 対話的追加指示 | 生成結果に対し音声で「もう少し柔らかく」等の修正指示 | P2 | 2 |
| F-31 | TTS送信前確認 | 予約直前に生成テキストを読み上げ、タップで承認 | P1 | 1.5 |
| F-32 | 固有名詞辞書 | 「ハーモニックデイ」「マラマハワイ」等のカスタム語彙 | P2 | 1.5 |

### 14.3 技術選択（未決定事項の暫定決定）

**暫定決定: OpenAI Whisper API を採用**

| 比較軸 | Whisper API | Google Speech-to-Text | Web Speech API |
|---|---|---|---|
| 日本語精度 | ◎ | ◎ | △〜○（端末依存） |
| コスト | $0.006/分 | $0.016-0.024/分 | 無料 |
| カスタム語彙 | △（プロンプト誘導のみ） | ✅（Phrase hints） | ❌ |
| APIシンプルさ | ◎ | ○ | ○ |
| ストリーミング | ❌（バッチのみ） | ✅ | ✅ |

**選定理由**:
- MVPはコスト最優先。圭一郎さん1人で月1000分使っても $6
- 固有名詞精度に実運用で問題が出たら Google STT（カスタム辞書）へ切替可能な抽象化を入れる

**抽象化方針**: 決定事項#6（AI API両対応）と同パターンで `packages/voice-provider/` にプロバイダ抽象を置く:
```typescript
interface VoiceProvider {
  transcribe(audio: Blob, opts: { vocabulary?: string[] }): Promise<Transcript>
}
// OpenAIWhisperProvider / GoogleSpeechProvider / WebSpeechProvider
```

### 14.4 新規APIエンドポイント

```
# 文字起こし単体
POST   /api/voice/transcribe
       body: multipart/form-data (audio file, max 25MB / 10分)
       res:  { transcript, detected_language, duration_seconds, provider, cost_usd }

# 音声→3案下書き生成（一気通貫）
POST   /api/voice/brainstorm
       body: multipart + { target_platforms[], tone, ng_rules[], additional_instructions }
       res:  {
         transcript,
         drafts: [{ platform, text, char_count, prompt_version_id }],
         session_id
       }

# 既存下書きに音声で修正指示（Phase 2）
POST   /api/voice/refine
       body: { post_id, audio_blob }
       res:  { transcript, refined_text, diff_summary }

# 固有名詞辞書
GET    /api/voice/vocabulary
POST   /api/voice/vocabulary        { term, pronunciation? }
DELETE /api/voice/vocabulary/:id

# 音声セッション履歴（監査・再生）
GET    /api/voice/sessions?from=&to=
GET    /api/voice/sessions/:id
DELETE /api/voice/sessions/:id
```

### 14.5 データモデル拡張

```
VoiceVocabulary (固有名詞辞書)
├── id (uuid, PK)
├── org_id (FK → Org)          # 決定#11 のマルチテナント設計に準拠
├── term (text)                  # 例: "ハーモニックデイ"
├── pronunciation (text, nullable) # 例: "はーもにっくでい"
├── language (default 'ja')
├── usage_count (int, 呼び出し回数)
├── created_at
└── updated_at

VoiceSession (音声ブレストセッション履歴)
├── id (uuid, PK)
├── user_id (FK → User)
├── org_id (FK → Org)
├── audio_url (R2 URL, 90日後自動削除)
├── transcript (text)
├── duration_seconds (int)
├── provider ('whisper' | 'google_stt' | 'web_speech')
├── cost_usd (numeric, 監査用)
├── generated_post_ids (uuid[], 生成された下書きID配列)
├── created_at
└── deleted_at (soft delete)
```

**RLS**: 決定#12 の org_id 方式をそのまま適用。`sns_accounts_safe` 的な公開ビューは不要（音声URL・トークンは含まれない）。

### 14.6 UI 増分設計

#### 14.6.1 シンプルモードホーム画面への追加（ペルソナA向け）

既存 4.3 ホーム画面の下部に固定マイクボタンを追加:

```
┌──────────────────────────────────┐
│  🏠 こんにちは、圭一郎さん        │
│  （既存: 今日の投稿・明日の投稿）   │
│  ...                              │
│  ┌─────────────────────────────┐ │
│  │   ＋ 新しい投稿を作る        │ │
│  └─────────────────────────────┘ │
│                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  ← 追加
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃                            ┃  │
│  ┃   🎤  話して投稿を作る     ┃  │  ← 画面下部固定
│  ┃   （長押しで録音）         ┃  │    80px高・大型
│  ┃                            ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│ [🏠] [📝] [📅] [⚙]              │
└──────────────────────────────────┘
```

#### 14.6.2 音声ブレストモーダル（録音中 → 生成結果）

```
─── 録音中 ─────────────────────
┌──────────────────────────────────┐
│  🎤 音声ブレスト                   │
│                                   │
│    🔴 録音中... 12秒               │
│    ▁▂▅▇▅▂▁  （波形表示）          │
│                                   │
│    [■ 停止して生成]               │
│                                   │
│  💡 話し方のコツ:                  │
│   • 日時・場所・金額を含める       │
│   • 固有名詞はゆっくり発音         │
│                                   │
│  [キャンセル]                      │
└──────────────────────────────────┘

─── 生成結果 ───────────────────
┌──────────────────────────────────┐
│  ✨ 3案を生成しました              │
│                                   │
│  📝 文字起こし                    │
│  「今日は自由が丘で波動体験会の    │
│   告知を書きたい。夕方6時から、    │
│   参加費3000円、初回の人向け」     │
│  [✏️ 修正] [🎤 再録音]            │
│                                   │
│  ━━━ X（140字）━━━                │
│  ┌────────────────────────────┐   │
│  │ 🔵 4/25(金) 18:00〜          │   │
│  │ 自由が丘で波動体験会を       │   │
│  │ 開催します🎵 ...           │   │
│  └────────────────────────────┘   │
│  [🔊 読み上げ] [この案で進める]   │
│                                   │
│  ━━━ Instagram（300-500字）━━━   │
│  ...                              │
│                                   │
│  ━━━ note（長文）━━━              │
│  ...                              │
│                                   │
│  🎤 [もう一度話して指示する] ← F-30 (Phase 2) │
└──────────────────────────────────┘
```

#### 14.6.3 TTS送信前確認（F-31）

誤送信防止のため、予約・即時投稿の直前に必須挿入:

```
┌──────────────────────────────────┐
│  🔊 内容を読み上げます             │
│                                   │
│  「自由が丘で波動体験会を開催     │
│   します。4月25日金曜日の...」    │
│                                   │
│  🟢━━━━━━━━━━○ 読み上げ中 (5/18秒) │
│                                   │
│  [⏸ 一時停止] [🔁 最初から]      │
│                                   │
│  内容は合っていますか？             │
│                                   │
│  [❌ 修正する] [✅ この内容で予約] │
└──────────────────────────────────┘
```

### 14.7 処理フロー

```
ユーザー: マイク長押し
  ↓
Browser: MediaRecorder API で音声キャプチャ (WebM/Opus)
  ↓ マイク離す
Frontend → POST /api/voice/brainstorm
          (multipart: audio blob + target_platforms + tone + vocabulary)
  ↓
Backend (Celery or FastAPI同期):
  1. VoiceSession作成 + R2に音声保存
  2. VoiceVocabulary → Whisper の prompt パラメータに語彙ヒント注入
  3. Whisper API → transcript
  4. 既存 AI Generator に transcript を渡す
     (既存プロンプト資産流用、target_platforms 分並列生成)
  5. NGチェック3層（決定#15）適用
  6. 3案をレスポンス、VoiceSession.generated_post_ids 更新
  ↓
Frontend: 3案表示 + TTS再生ボタン有効化
  ↓ ユーザー承認
既存の POST /api/posts + /schedule フローに合流
```

### 14.8 シニア配慮（決定#26/#27との整合）

- マイクボタン: **画面下部固定・80px高**（誤タップ回避）
- 録音中: **視覚波形 + 秒数カウンター**で状態を明示
- **ヘルプモードON時**: マイクボタン横に `?` アイコン → Popoverで使い方
- 誤認識の修正は **「手打ち」または「再録音」の二択のみ**（複雑な編集UIを出さない）
- TTSはデフォルト **0.9倍速・大きめボリューム**（設定で調整可）
- 長時間録音（60秒超）は録音中にアラート（「長すぎると認識精度が落ちます」）

### 14.9 セキュリティ・プライバシー

- 音声データは **R2 に 90日保持 → 自動削除**（監査・改善用途、プライバシーポリシーに明示）
- ユーザー設定で **「音声履歴を残さない」オプション**（`users.ui_preferences.voice_history_enabled = false` → 文字起こし完了後即削除）
- Whisper API 送信データは OpenAI の学習に使用されない（Zero Retention Policy に準拠、API仕様確認済み）
- ブラウザのマイク権限は初回のみ要求、以降永続化（iOS Safari で要実機確認）

### 14.10 コスト試算

| 項目 | 単価 | 圭一郎さん想定（月30セッション×30秒） | 一般ユーザー（月10セッション） |
|---|---|---|---|
| Whisper API | $0.006/分 | $0.09 | $0.03 |
| LLM生成（3案並列） | 既存 $0.032/投稿 × 3 | $2.88 | $0.96 |
| R2ストレージ | ~$0.015/GB・月 | 〜$0.01 | 〜$0.01 |
| **合計** | | **~$3/月** | **~$1/月** |

既存 MVP コスト想定 ~$5-15/月 に対し、音声機能追加コストは **10-20% 程度の増分**。

### 14.11 Phase 判断

| Phase | 実装範囲 |
|---|---|
| **Phase 1.5** | F-28（マイクボタン）、F-29（リアルタイムブレスト）、F-31（TTS確認）、F-32（辞書 基本） |
| **Phase 2** | F-30（対話的追加指示）、F-32（辞書 高度化）、Google STT 切替オプション |

**Phase 1.5 に組み込む根拠**:
- 既存 F-16（音声ファイル→投稿）と実装基盤（Whisper + AI Generator）を共有できる
- プライマリペルソナA（圭一郎さん）が **MVP時点で使える状態**を作ることが joyfoundation 要件の本質
- UI増分は既存画面への追加のみ、DB/API も軽微

### 14.12 実装タスク案（既存Sprint計画への追加）

既存の 30 Issue / 4 Sprint 計画（`IMPLEMENTATION_PLAN.md`）に対し、以下 7 Issue の追加を想定:

```
Sprint 4 (Phase 1.5 の末尾 or Phase 1.5.5) に追加:
- VOICE-001: packages/voice-provider/ 抽象化パッケージ（Whisper実装込み）
- VOICE-002: POST /api/voice/transcribe エンドポイント
- VOICE-003: POST /api/voice/brainstorm エンドポイント（AI Generator連携）
- VOICE-004: フロント マイクボタンコンポーネント（shadcn拡張）
- VOICE-005: 音声ブレストモーダル UI
- VOICE-006: TTS送信前確認モーダル（既存投稿作成フローへの割り込み）
- VOICE-007: VoiceSession/VoiceVocabulary マイグレーション + RLS + 90日自動削除ジョブ
```

**見積もり**: +2〜3週（既存 7-8週 → 合計 9-11週）

### 14.13 未解決事項

- [ ] **圭一郎さんの音声サンプルでの Whisper 精度実測** — `scripts/voice-poc/whisper_precision_test.py` で先行検証
- [ ] **iOS Safari のマイク権限UX** — 実機検証が必要
- [ ] **TTSエンジン選定** — ブラウザ SpeechSynthesis API（無料）vs OpenAI TTS（高品質 $15/1M文字）
- [ ] **オフライン時の挙動** — 録音のみローカル保存し、オンライン復帰時に送信するか

### 14.14 次アクション

1. 本設計を `IMPLEMENTATION_PLAN.md` の Sprint 計画に反映（VOICE-001〜007 を追記）
2. `scripts/voice-poc/whisper_precision_test.py` を作成 → 圭一郎さんの音声サンプル1本で精度計測
3. 結果次第で Whisper 維持 / Google STT 切替を本決定
4. `feat/voice-input` ブランチを切るのは VOICE-001 着手時（main 上の設計追記フェーズ完了後）

---

## 15. 無料スタック移行計画 v0.1（販売化を見据えた固定費ゼロ設計）

**策定日**: 2026-04-22
**ステータス**: Draft（実装着手前の設計フェーズ）
**影響範囲**: バックエンドのランタイム / ジョブ / リアルタイム通知レイヤ

### 15.1 背景と目的

本アプリは将来的に **SaaS 販売** を目標とする。Phase 1 MVP は FastAPI + Celery (Worker/Beat) + Redis の構成で完成しているが、この構成を有料ホスティング（Railway 等）に乗せると **固定費 $5〜10/月が発生** する。利用者0の MVP 段階から固定費が発生すると、販売収益と運用コストのスケール連動が崩れ、ビジネスモデルの制約になる。

方針: **利用者0のアイドル時は固定費0円、利用者増加時は従量で各サービスが自然に有料化** するアーキテクチャに移行する。

### 15.2 構成比較

| レイヤ | 現行 (Phase 1 MVP) | 移行後 (D案) | 理由 |
|---|---|---|---|
| フロント | Next.js (Vercel Hobby) | **同じ** | Hobby Free で商用可否は規約確認要 |
| 認証・DB | Supabase Postgres | **同じ** | Free tier 500MB |
| API | FastAPI on Railway | **FastAPI on Cloud Run** | Scale-to-zero、無料枠内 |
| ジョブスケジューラ | Celery Beat | **Supabase pg_cron** | DB内完結、無料、運用コスト0 |
| ジョブ実行 | Celery Worker (Redis 経由) | **FastAPI endpoint を GitHub Actions Cron が叩く**（既存 `auto_post.yml` 踏襲） | GH Actions 無料枠内、Cloud Run と相性良 |
| リアルタイム通知 | FastAPI WebSocket + Redis PubSub | **Supabase Realtime**（notifications テーブル INSERT 購読） | 無料、Redis 不要 |
| ストレージ | Cloudflare R2 | **同じ** | 無料枠内（10GB-month + 1M Class A ops/月） |
| メール | （未実装） | **Resend** | 3000通/月無料、SMTP Transactional |

### 15.3 削除されるコンポーネント

1. **Celery 関連一式**
   - `apps/api/app/tasks/celery_app.py` / `scheduled_posts.py`
   - `apps/api/railway.worker.json` / `railway.beat.json`
   - `celery` / `redis` の Python 依存
2. **Redis**
   - broker 用途 → pg_cron + GH Actions で代替
   - PubSub 用途 → Supabase Realtime で代替
3. **FastAPI WebSocket 実装**
   - `apps/api/app/api/notifications_ws.py` → Supabase Realtime 購読に置き換え

### 15.4 追加/変更されるコンポーネント

1. **Supabase pg_cron**
   - `supabase/migrations/` に cron 設定 SQL を追加
   - 毎分 `posts` テーブルから予約時刻到達の行を検出し、`publish_queue` テーブルに INSERT
2. **GitHub Actions Cron**（既存 `auto_post.yml` のパターン流用）
   - 5分毎に `POST /internal/publish/flush` を叩く
   - 認証: `X-Internal-Token` ヘッダー（GH Secrets）
3. **Cloud Run デプロイ設定**
   - `apps/api/service.yaml`（Cloud Run YAML）
   - `.github/workflows/deploy-backend-cloudrun.yml`（既存 deploy-backend.yml を置換）
   - Workload Identity Federation で GH→GCP 認証
4. **Supabase Realtime 購読（Web）**
   - `apps/web/src/hooks/useNotifications.ts` を `supabase-js` の `.channel().on('postgres_changes', ...)` に書き換え

### 15.5 ARCH-001〜005 実装タスク案

| ID | タスク | 工数 | 依存 |
|---|---|---|---|
| **ARCH-001** | Celery Beat → pg_cron + GitHub Actions Cron 移行 | 0.5日 | なし |
| **ARCH-002** | Celery Worker → FastAPI 内部エンドポイント + GH Actions 呼び出し置換 | 0.5日 | ARCH-001 |
| **ARCH-003** | Redis PubSub → Supabase Realtime 移行（WebSocket 実装削除） | 0.5日 | なし |
| **ARCH-004** | FastAPI デプロイ先 Railway → Cloud Run 切替 | 0.5日 | ARCH-001〜003 |
| **ARCH-005** | Resend 導入（認証メール / 投稿結果通知） | 0.3日 | ARCH-004 |

合計: **2〜3日**

### 15.6 Cloud Run 採用の根拠と制約

**採用理由**:
- **Dockerfile 既存のまま使える**（現行 `apps/api/Dockerfile` が uvicorn で PORT=8000 起動）
- **Scale-to-zero** でアイドル時の費用 0
- Google Cloud 無料枠: 毎月 **200万リクエスト + 36万 vCPU秒 + 18万 GiB秒**
- リージョン選択可（`asia-northeast1` 東京）

**制約**:
- **コールドスタート 1〜3秒**（初回リクエスト or 長時間アイドル後）
- **WebSocket 長時間接続は課金対象**（→ Realtime 移行で回避）
- **バックグラウンドジョブ非推奨**（リクエスト処理中のみCPU保証） → Celery 撤廃と整合

**スケール時の対処**:
- 利用者増でコールドスタートが問題 → `min-instances=1` に設定（月 $5〜相当の課金開始）
- Supabase Free 500MB 到達 → Pro $25/月
- これらは **販売収益が発生した後の話** なので計画的に昇格可

### 15.7 監視と昇格トリガー

販売化後に備え、以下のメトリクスを月次確認:

| サービス | 無料枠 | 警告閾値 | 昇格先 |
|---|---|---|---|
| Supabase DB | 500 MB | 400 MB | Pro $25/月 |
| Supabase MAU | 50,000 | 40,000 | Pro $25/月 |
| Cloud Run req | 200万/月 | 150万/月 | 従量 ($0.40/100万req) |
| Cloud Run CPU | 36万 vCPU秒 | 28万 | 従量 |
| Vercel 帯域 | 100 GB/月 | 80 GB | Pro $20/月 |
| R2 ストレージ | 10 GB-month | 8 GB | 従量 ($0.015/GB-month) |
| Resend 送信 | 3000/月 | 2400 | Pro $20/月 |

### 15.8 リスクと緩和策

| リスク | 緩和策 |
|---|---|
| Cloud Run コールドスタート UX 悪化 | ログイン時に `/health` を先行打鍵してウォームアップ |
| GH Actions Cron 遅延（高負荷時） | 投稿は1件ずつ処理、DB側で `locked_at` で排他制御 |
| pg_cron 停止（Supabase障害） | GH Actions 側の cron も投稿対象を直接ポーリング可能な構造にする（二重化） |
| Realtime 接続切断 | `useNotifications` フックで自動再接続（exponential backoff） |
| Supabase Free 仕様変更 | `#12 Supabase運用検討` タスクで年次レビュー |

### 15.9 Phase 1 MVP コードとの差分

Phase 1 MVP は Railway 前提で実装完了（#22 マージ）。この設計書は **追加の feature branch (`feat/free-stack-migration`) で段階的に実装** する。`main` ブランチの既存コードは **破棄ではなく漸進的に置換**:

1. ARCH-003 から着手（Realtime 移行は独立・リスク低）
2. ARCH-001/002 で Celery を削除
3. ARCH-004 で Cloud Run デプロイ
4. Railway 関連設定 (`railway.*.json`) は最終削除

### 15.10 次アクション

1. 本設計書を `docs/free-stack-migration` ブランチで PR 化
2. ARCH-001〜005 の Codex ブリーフィングを `docs/codex_brief_ARCH-00*.md` に作成
3. 実装着手は別 feature branch で（`feat/arch-001-pg-cron-migration` 等 ARCH ごと）
4. 完了後、圭一郎さん環境へのデプロイ（P2 Vercel + D案 Cloud Run）

### 15.11 未解決事項

- [ ] **Vercel Hobby Free の商用利用規約**確認（SaaS 販売が規約違反にならないか）
- [ ] **Cloud Run の Workload Identity Federation** 設定手順（GH Actions → GCP 認証）
- [ ] **Supabase pg_cron** のタイムゾーン設定（JST vs UTC）
- [ ] **Realtime の接続数上限**（Free で concurrent 200接続、販売化時は要Pro）
- [ ] **販売モデル**の粗案（Freemium / Per-seat / Per-org / Usage-based）→ 別設計書（BIZ-001）で扱う
