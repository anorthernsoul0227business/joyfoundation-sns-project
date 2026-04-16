# note.com連携 法務/規約確認 + 実装設計（Codex壁打ち結果）

**作成日**: 2026-04-16
**関連**: APP_DESIGN_SPEC.md セクション13 優先アクション#5

---

## 前提と総評

- note.comは**公式の投稿APIを提供していない**（2026年4月時点）。今後の公開予定も「未定」。
- 非公式APIエンドポイント（`/api/v1/text_notes`）は**405 Not Allowedを返す**状態で、投稿操作は明示的にブロックされている。
- 利用規約（第22版 2026年1月15日制定）では「スパム的な活動」を禁止。自動投稿は直接言及されていないが、**大量自動化はスパムと見なされるリスクが高い**。
- note proは月額¥80,000の法人向けプランだが、**投稿API機能は含まれていない**。
- **結論: 自動投稿は規約・技術・事業リスクの3点で非推奨。「下書き補助+手動投稿」が現実解。**

---

## 1. 規約分析

### 1.1 note利用規約（第22版）の関連条項

| 条項 | 内容 | 自動投稿との関連 |
|---|---|---|
| 禁止事項（スパム） | 「スパム的な活動」の禁止 | 大量自動投稿はスパムと見なされる可能性 |
| 禁止事項（迷惑行為） | 「他の利用者および当社への迷惑・損害やそのおそれを発生させる行為」の禁止 | サーバー負荷を発生させる自動化は該当し得る |
| 禁止事項（技術的措置の回避） | 「デジタルコンテンツを保護するために施された技術的措置を回避・無効化すること」の禁止 | 非公式API利用はこれに該当する可能性 |
| サービス停止 | 規約違反時のアカウント停止・削除権限 | 事前警告なしの停止も規約上は可能 |

### 1.2 リスク評価マトリクス

| 連携方式 | 規約リスク | 技術リスク | 事業リスク | 総合評価 |
|---|---|---|---|---|
| **非公式API（POST）** | 高（禁止されたエンドポイント） | 高（405エラーで動作不可） | 高（アカウント停止→過去記事消失） | ❌ 不可 |
| **Playwright/Selenium自動化** | 高（技術的措置の回避に該当） | 高（UI変更で即座に破綻） | 高（同上） | ❌ 不可 |
| **非公式API（GET:読み取り）** | 中（データ取得のみ） | 中（仕様変更リスク） | 低（投稿データに影響なし） | △ 限定的に可 |
| **RSS連携（読み取り）** | 低（公開情報の利用） | 低（標準規格） | 低 | ○ 推奨 |
| **iframe/oEmbed埋め込み** | なし（公式サポート） | 低 | 低 | ◎ 推奨 |
| **手動投稿 + アプリ側で下書き生成** | なし | なし | なし | ◎ 最推奨 |

### 1.3 App Store審査への影響

| 審査基準 | 自動投稿の影響 | 判定 |
|---|---|---|
| 4.2 Design: Minimum Functionality | 非公式API依存の機能は「最小限の機能」に該当するリスク | ⚠️ |
| 5.2.1 Legal: General | 他社サービスの規約に違反する機能は審査でリジェクトされる可能性 | ⚠️ |
| 5.2.3 Legal: Intellectual Property | 非公式APIの利用は知的財産権侵害と見なされる可能性 | ⚠️ |

---

## 2. note連携の段階設計（推奨）

### 2.1 フェーズ分割

```
Phase 1 (MVP): 下書き補助モード
  └── アプリ内でnote記事を作成・編集 → クリップボードコピー or テキストファイルDL → 手動投稿

Phase 2: ワンクリック支援モード
  └── note投稿画面をWebViewで開く → テキスト自動入力（ユーザーが確認後に手動で「投稿」ボタンを押す）
  └── ※ この方式も規約グレーゾーンのため、実装前に note社に事前確認を推奨

Phase 3+: 公式API対応（noteがAPIを公開した場合）
  └── 公式APIが公開されたら即座に対応
  └── note pro API（法人向け）が先行提供される可能性もある
```

### 2.2 Phase 1: 下書き補助モード（詳細設計）

#### 機能概要

アプリ内でnote記事を完全に作成・編集し、最終的にユーザーが手動でnoteに投稿する。投稿作業は約3分で完了する。

#### UI設計

```
┌──────────────────────────────────────────────────────┐
│  ← note記事プレビュー                    [コピー 📋] │
│                                                       │
│  ┌─ タイトル ──────────────────────────────────────┐ │
│  │ 自然音が変える「休息の質」                        │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─ 本文プレビュー ────────────────────────────────┐ │
│  │                                                   │ │
│  │ ## はじめに                                       │ │
│  │                                                   │ │
│  │ 「最近、ぐっすり眠れていますか？」                 │ │
│  │                                                   │ │
│  │ 日本人の平均睡眠時間は6時間22分。                 │ │
│  │ OECD加盟国の中で最も短いというデータがあります。  │ │
│  │                                                   │ │
│  │ そんな現代人の「休息の質」を変える鍵として         │ │
│  │ 注目されているのが「自然音」です。                 │ │
│  │ ...                                               │ │
│  │                                                   │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─ 投稿ガイド ────────────────────────────────────┐ │
│  │  📋 以下の手順で投稿してください（約3分）:        │ │
│  │                                                   │ │
│  │  1. 上の「コピー」ボタンを押す                    │ │
│  │  2. note.comを開く → [noteを開く 🔗]             │ │
│  │  3. 「投稿」→「テキスト」を選択                  │ │
│  │  4. タイトルと本文をペースト                      │ │
│  │  5. 画像を添付（下のダウンロードボタンから取得）   │ │
│  │  6. 「公開設定」→「投稿」                        │ │
│  │                                                   │ │
│  │  ⏱ 投稿完了後、ここに戻って「投稿済み」を        │ │
│  │    押してください → カレンダーに反映されます      │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─ 画像 ─────────────────────────────────────────┐  │
│  │  ┌────┐ ┌────┐                                 │  │
│  │  │img1│ │img2│  [画像をダウンロード 📥]         │  │
│  │  └────┘ └────┘                                 │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  [✅ 投稿済みにする]         [✏️ 編集に戻る]         │
└──────────────────────────────────────────────────────┘
```

#### データモデル追加

```sql
-- PostTarget に note 用の追加フィールド
-- platform = 'note' の場合:
--   status: 'draft' → 'ready_to_post' → 'manually_posted'
--   platform_post_url: ユーザーが手動入力（オプション）

-- note記事は Post.text とは別に長文テキストを持つ
CREATE TABLE public.note_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body_markdown TEXT NOT NULL,        -- Markdown形式の本文
  body_html TEXT,                     -- プレビュー用HTML
  word_count INT,
  estimated_read_time INT,            -- 分
  tags JSONB,                         -- noteのタグ（最大5個）
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### コピー機能の実装

```typescript
// フロントエンド: クリップボードコピー
async function copyNoteArticle(article: NoteArticle) {
  // noteはMarkdownをそのままペーストすると整形される
  const content = `${article.title}\n\n${article.body_markdown}`;

  try {
    await navigator.clipboard.writeText(content);
    toast.success('クリップボードにコピーしました');
  } catch {
    // フォールバック: テキストエリアを使ったコピー
    fallbackCopy(content);
  }
}

// note投稿ページを新しいタブで開く
function openNoteEditor() {
  window.open('https://note.com/notes/new', '_blank');
}
```

#### 「投稿済み」フローの設計

```
ユーザーが「投稿済みにする」ボタンを押す
  │
  ├── オプション: note記事URLを入力（任意）
  │   └── 入力された場合 → PostTarget.platform_post_url に保存
  │
  ├── PostTarget.status → 'manually_posted'
  ├── PostTarget.published_at → now()
  │
  ├── カレンダー上で「投稿済み」表示に変更
  │
  └── 通知: 「note記事を投稿済みにしました」
```

---

## 3. note記事生成のAI対応

### 3.1 X/IGとの違い

| 項目 | X | Instagram | note |
|---|---|---|---|
| 文字数 | 280（重み付き） | 2,200 | 制限なし（推奨1,500-2,500） |
| 構成 | 1ツイート完結 | キャッチ+本文+CTA | 導入+セクション+データ+CTA |
| 画像 | 補助的 | メイン | 記事内挿入 |
| トーン | カジュアル | やわらかい・知的 | 専門的・読み応え |
| 目的 | 認知・拡散 | 関心・保存 | 教育・信頼構築 |

### 3.2 note用プロンプト設計

```yaml
# prompts/generation/note_article.yaml
system: |
  あなたはサウンドヒーリング・自然音に関する専門記事のライターです。
  以下のルールに従って、note.com向けの記事を作成してください。

  ## 記事構成ルール
  1. **タイトル**: 30-50文字。知的好奇心を刺激する。「?」や「〜とは」を活用
  2. **導入（200-300字）**: 問いかけ or 共感で始める。読者の悩みに寄り添う
  3. **本文（3-4セクション、各300-500字）**:
     - 各セクションに見出し（##）を付ける
     - 1つのセクション = 1つのメッセージ
     - 科学的データや研究結果を根拠として提示
     - 「〜と言われています」「〜という報告があります」等の慎重な表現
  4. **実践者の声（100-200字）**: 引用ブロックで体験談（あれば）
  5. **まとめ（100-200字）**: ポイントを3つに絞って箇条書き
  6. **CTA（50-100字）**: オンラインセミナーへの誘導

  ## NGルール
  - 「効果があります」「治ります」等の断言表現は禁止
  - 「〜と感じる方もいます」「〜のサポートとして」に言い換え
  - 医療行為との混同を避ける

  ## トーン
  - 専門的だが堅すぎない
  - データに基づく知的な印象
  - 読者への敬意と温かみ

user: |
  ## 元資料
  {source_material}

  ## 追加指示
  {additional_instructions}

  上記の資料をもとに、note.com向けの記事を作成してください。
  Markdown形式で出力してください。
```

### 3.3 X/IG投稿との連携（クロスプラットフォーム）

```
1つの資料から3つのコンテンツを同時生成:

資料（PDF/音声） 
  ├── X投稿（180文字のエッセンス）
  │     └── "自然音の低音成分が副交感神経を活性化するという研究報告が。
  │          寝る前の15分、小川のせせらぎを聴くだけでも変化を感じる方が
  │          多いそうです #サウンドヒーリング"
  │
  ├── IG投稿（300-500文字の知識カード）
  │     └── "【保存推奨】眠れない夜に試してほしい「自然音」の選び方
  │          ━━━━━━━━━━━━━━━━
  │          実は音には「周波数」があり..."
  │
  └── note記事（1,500-2,500文字の深掘り）
        └── "# 自然音が変える「休息の質」
             ## はじめに
             「最近、ぐっすり眠れていますか？」..."
```

---

## 4. note記事のRSS活用

### 4.1 RSS連携設計（公式サポート）

noteはRSSフィードを公式サポートしている。アプリ側でRSSを活用し、投稿済みnote記事をカレンダーに自動反映する。

```python
import feedparser

NOTE_RSS_URL = "https://note.com/{username}/rss"

def sync_note_articles(username: str) -> list[dict]:
    """noteのRSSフィードから投稿済み記事を取得"""
    feed = feedparser.parse(NOTE_RSS_URL.format(username=username))

    articles = []
    for entry in feed.entries:
        articles.append({
            'title': entry.title,
            'url': entry.link,
            'published_at': entry.published,
            'summary': entry.summary,
        })

    return articles

def match_with_calendar(articles: list[dict], posts: list[Post]):
    """
    RSS記事とカレンダー上のnote下書きをマッチング
    → 手動投稿済みの確認を自動化
    """
    for article in articles:
        # タイトルの類似度でマッチング
        matching_post = find_best_match(article['title'], posts)
        if matching_post and matching_post.status == 'ready_to_post':
            matching_post.status = 'manually_posted'
            matching_post.platform_post_url = article['url']
            matching_post.published_at = article['published_at']
```

### 4.2 oEmbed埋め込み

```typescript
// note記事をアプリ内で表示（公式サポート）
// noteのURLを入力 → oEmbedでリッチプレビュー
async function getNoteEmbed(noteUrl: string) {
  const response = await fetch(
    `https://note.com/api/v2/oembed?url=${encodeURIComponent(noteUrl)}`
  );
  return response.json();
  // { html: '<iframe ...>', width: 600, height: 400, ... }
}
```

---

## 5. 将来のnote公式API対応への備え

### 5.1 API公開の可能性シナリオ

| シナリオ | 確率 | 対応 |
|---|---|---|
| note proに投稿APIが追加（法人限定） | 中 | note pro契約（¥80,000/月）で対応。ユーザー向けにはプロ/ビジネスプランで提供 |
| noteが公開APIをリリース（全ユーザー） | 低 | 即座に対応。PostTarget + publisher抽象化で1-2週間で統合可能 |
| noteがサードパーティ連携プログラムを開始 | 中 | パートナー申請を行い、正式な連携を確保 |
| 現状維持（API非公開のまま） | 高 | 下書き補助モードを継続。RSS連携で投稿済み管理を自動化 |

### 5.2 抽象化設計（API公開時に即座に対応）

```python
# services/publisher/base.py
class BasePublisher(ABC):
    @abstractmethod
    async def publish(self, text: str, media: list, account: SnsAccount) -> PublishResult:
        pass

    @abstractmethod
    async def supports_scheduling(self) -> bool:
        pass

# services/publisher/note_publisher.py
class NotePublisher(BasePublisher):
    """
    Phase 1: 下書き補助（実際の投稿はしない）
    Phase 3+: 公式API経由の自動投稿（API公開後）
    """

    async def publish(self, text: str, media: list, account: SnsAccount) -> PublishResult:
        if not self._has_official_api():
            # Phase 1: 下書きを準備するだけ
            return PublishResult(
                status='ready_to_post',
                message='note記事の下書きが準備できました。手動で投稿してください。',
                requires_manual_action=True,
            )
        else:
            # Phase 3+: 公式API経由
            return await self._publish_via_api(text, media, account)

    async def supports_scheduling(self) -> bool:
        return False  # noteはAPI予約投稿未サポート（Phase 3+で変更の可能性）

    def _has_official_api(self) -> bool:
        # 環境変数 or Feature Flagで制御
        return os.getenv('NOTE_OFFICIAL_API_ENABLED', 'false') == 'true'
```

---

## 6. 法務上の推奨事項

### 6.1 事前対応（実施推奨）

| # | アクション | 理由 | 優先度 |
|---|---|---|---|
| 1 | **note社への事前問い合わせ** | 「下書き補助+手動投稿」モデルの合法性を確認。「将来API公開の予定は？」も確認 | P0 |
| 2 | **利用規約の継続監視** | 規約改定（年2-3回）時に自動化関連の変更をチェック | P1 |
| 3 | **App Storeリジェクト対策** | note連携機能の説明文で「手動投稿」を明記。非公式APIは一切使用しない | P1 |
| 4 | **免責事項の記載** | アプリ内に「note記事は手動投稿が必要です」の説明を明記 | P2 |

### 6.2 問い合わせ文面テンプレート

```
件名: SNS一括管理アプリからのnote記事投稿補助機能について

note株式会社 御中

お忙しいところ恐れ入ります。
SNS投稿を一括管理するアプリを開発している[会社名]の[名前]と申します。

現在、X・Instagram等のSNS投稿をカレンダーで管理し、
予約投稿を行うアプリを開発しております。

note.com向けの機能として、以下のアプローチを検討しております:
1. アプリ内でnote記事の下書きを作成
2. ユーザーがクリップボードにコピー
3. note.comの投稿画面でユーザー自身が手動で投稿

上記の「下書き補助」機能について、貴社の利用規約上、
問題がないかご確認いただけますでしょうか。

また、今後法人向けに投稿APIの公開予定がございましたら、
パートナー連携のご相談もさせていただければ幸いです。

何卒よろしくお願いいたします。
```

### 6.3 note社への問い合わせ先

| 連絡先 | 用途 |
|---|---|
| [note pro お問い合わせ](https://biz.note.com/) | 法人向け連携の相談 |
| [noteヘルプセンター](https://www.help-note.com/) | 規約の確認 |

---

## 7. 競合分析: 他ツールのnote対応状況

| ツール | note対応 | 方式 |
|---|---|---|
| Buffer | ❌ | 非対応 |
| Hootsuite | ❌ | 非対応 |
| Later | ❌ | 非対応 |
| SocialDog | ❌ | X特化 |
| Postiz (OSS) | ❌ | 非対応 |

**→ 競合ツールもnoteには対応していない。** 下書き補助モードでも「noteに対応している」という差別化は十分に有効。

---

## 8. 決定事項まとめ

| # | 項目 | 決定 | 理由 |
|---|---|---|---|
| 1 | Phase 1の方式 | **下書き補助+手動投稿** | 規約・法務リスクゼロ |
| 2 | 非公式API利用 | **完全禁止** | 405ブロック済み、規約違反リスク、App Store審査リスク |
| 3 | Playwright/Selenium | **完全禁止** | 規約違反、UI変更で破綻、保守コスト大 |
| 4 | RSS連携 | **採用（投稿済み自動検知）** | 公式サポート、リスクなし |
| 5 | oEmbed | **採用（記事プレビュー）** | 公式サポート、リスクなし |
| 6 | note社への事前確認 | **実施推奨** | 下書き補助モデルの合法性確認 + API公開予定の確認 |
| 7 | publisher抽象化 | **API公開に即応できる設計** | NotePublisher.publish()で分岐 |

---

## 9. 優先アクション

| # | アクション | 工数 | タイミング |
|---|---|---|---|
| 1 | note社への問い合わせ（テンプレート使用） | 1時間 | 今すぐ |
| 2 | note_articles テーブル作成 | 0.5日 | Phase 1 DB設計時 |
| 3 | note記事生成プロンプト作成 | 1日 | Phase 1.5 AI生成機能実装時 |
| 4 | 下書き補助UI実装（コピー+ガイド） | 2日 | Phase 1.5 |
| 5 | RSS連携（投稿済み自動検知） | 1日 | Phase 2 |
| 6 | 利用規約変更の定期チェック体制構築 | 0.5日 | Phase 2 |
