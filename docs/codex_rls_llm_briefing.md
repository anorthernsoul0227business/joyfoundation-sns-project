# Codex壁打ち指示書 R3: RLS設計レビュー + LLM品質評価基盤

## あなたへの依頼

SNS Calendar App（カレンダーにドラッグするだけで複数SNSに自動投稿できるアプリ）の設計書を添付します。
以下の2テーマについて、設計レビューと具体的な実装提案をお願いします。

---

## テーマ1: Supabase RLS（Row Level Security）設計レビュー

### 背景

- 認証基盤として **Supabase Auth + PostgreSQL** を採用決定済み
- マルチテナント（将来的に複数ユーザーがそれぞれのSNSアカウントを管理）
- Phase 1はシングルユーザー運用だが、Phase 2以降でチーム・承認フローを追加予定
- SNSトークン（access_token, refresh_token）はDBに暗号化保存（AES-256-GCM）

### データモデル（確定済み）

```
User (id, email, password_hash, display_name, ui_mode, created_at, updated_at)
SnsAccount (id, user_id FK→User, platform, platform_user_id, access_token_enc, refresh_token_enc, token_expires_at)
Post (id, user_id FK→User, status, text, scheduled_at, published_at)
PostTarget (id, post_id FK→Post, sns_account_id FK→SnsAccount, platform_post_id, status, error_message, idempotency_key, attempt_count)
PostMedia (id, post_id FK→Post, sort_order, original_url, media_type, width, height, file_size)
Notification (id, user_id FK→User, type, title, body, post_id FK→Post, read)
GenerationJob (id, user_id FK→User, status, target_platforms, num_days, start_date, tone, ng_rules)
GenerationSource (id, job_id FK→GenerationJob, source_type, file_url, extracted_text)
NgRulePreset (id, user_id FK→User nullable, name, rules, is_default)
```

### 聞きたいこと

1. **RLSポリシー設計**: 各テーブルに対するSELECT/INSERT/UPDATE/DELETEの具体的なRLSポリシーを提示してほしい
2. **サービスロール vs ユーザーロール**: Celery workerからの投稿実行（バックエンド）はRLSをバイパスすべきか、service_roleキーで操作すべきか
3. **チーム機能への拡張**: Phase 2でチーム・承認フローを追加する場合、今から仕込んでおくべきテーブル構造やRLSの拡張ポイント
4. **トークン保護**: access_token/refresh_tokenカラムへのRLSによるアクセス制限（フロントエンドからは見えなくする）
5. **NgRulePreset共有**: user_id=NULLのシステムデフォルトプリセットと、ユーザー固有のプリセットをRLSで安全に共存させる方法
6. **パフォーマンス**: RLSが有効なテーブルでのインデックス戦略（カレンダー表示で日付範囲+user_idクエリが頻繁）
7. **セキュリティ落とし穴**: SupabaseのRLSでよくあるミス・見落とし

---

## テーマ2: LLM品質評価基盤

### 背景

- AI記事生成機能（F-11〜F-17）: 資料（PDF/音声/URL）→ 投稿テキスト自動生成
- **対象SNS**: X（280文字制限）、Instagram（キャプション2,200文字）
- **日本語ネイティブ**: ターゲットユーザーは日本の事業者
- **LLM**: Claude API + OpenAI API 両対応（プロバイダ抽象化済み）
- **プロンプト管理**: Git管理YAML + テナント差分はDB（ハイブリッド）
- **NGルール**: 効果断言禁止（薬機法）、改行前句読点なし、ハッシュタグルール等

### 現在の課題

1. 生成品質を定量的に測る仕組みがない
2. Claude vs OpenAI のどちらが良いかを判断する基準がない
3. プロンプト変更時のリグレッション検知ができない
4. 媒体別（X vs IG）でトーンや文字数の適切さが異なるが、統一的に評価したい
5. NGルール違反を自動チェックしたい

### 聞きたいこと

1. **評価メトリクス設計**: SNS投稿テキストの品質を測るメトリクスセット（日本語特有の評価軸を含む）
2. **評価データセット**: ゴールドスタンダードとなる評価セットの作り方（何件必要か、どうアノテーションするか）
3. **自動評価 vs 人間評価**: LLM-as-a-Judge（Claude/GPT-4で評価）はSNS投稿に有効か。その場合の評価プロンプト設計
4. **ABテスト基盤**: プロンプトバージョン間の比較テスト設計（offline評価 + online指標）
5. **NGルール自動チェック**: 薬機法・景表法系のNG表現を自動検知するアーキテクチャ（ルールベース vs LLM vs ハイブリッド）
6. **プロンプトバージョニング**: どの投稿がどのprompt_versionで生成されたかのトレーサビリティ設計
7. **コスト最適化**: 評価パイプラインのランニングコスト試算と削減戦略
8. **媒体別評価**: X（短文）とIG（長文）で評価基準をどう分けるか

### NGルール例（現在運用中）

```yaml
ng_rules:
  - id: yakuji_law
    name: 薬機法対応
    patterns:
      - "効果があります"
      - "治ります"
      - "改善します"
    replacement_hint: "〜と言われています" "〜を感じる方もいます"

  - id: punctuation
    name: 改行前句読点なし
    pattern_regex: "[、。]\\n"

  - id: hashtag_fixed
    name: 固定ハッシュタグ
    required: ["#KITAサウンドヒーリング"]
```

### トーン要件（媒体別）

| 媒体 | トーン | 例 |
|---|---|---|
| X | カジュアル・親しみやすい・短い | 「自然音、聴いてますか？実は低い音ほど体がゆるむんです」 |
| IG | やわらかい・知的・読み応えある | 「【保存推奨】音の高さと体の反応━━━━━━低音は副交感神経を...」 |

---

## 参考: 確定済み技術スタック

- Frontend: Next.js 15 + TypeScript + Tailwind + shadcn/ui
- Backend: Python FastAPI
- DB: PostgreSQL (Supabase)
- Auth: Supabase Auth
- ジョブキュー: Celery + Redis
- ファイルストレージ: Cloudflare R2
- ホスティング: Vercel (Frontend) + Railway (Backend)

## 回答形式

各テーマについて以下の形式で回答してください:

1. **推奨アプローチ**: 具体的な実装案（コード例・SQL例を含む）
2. **リスク**: 各アプローチのリスクと対策
3. **トレードオフ**: 代替案との比較
4. **優先アクション**: 今すぐやるべきこと（実行順）
