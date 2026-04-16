# LLM品質評価基盤 設計書（Codex壁打ち結果）

**作成日**: 2026-04-16
**関連**: APP_DESIGN_SPEC.md セクション13 優先アクション#4

---

## 前提と総評

- SNS投稿テキストの品質評価は、一般的なNLPタスク（要約・翻訳）と異なり、**エンゲージメント**と**ブランドトーン**が重要。
- 日本語のSNS投稿評価は英語圏と異なる基準が必要（敬語レベル、句読点ルール、絵文字/記号の使い方）。
- **LLM-as-a-Judge**はSNS投稿評価に有効。ただし位置バイアス（40%のGPT-4不整合）と冗長バイアス（15%のスコア膨張）に注意。
- Phase 1では**オフライン評価パイプライン**を構築し、Phase 2で**オンライン指標（エンゲージメント連動）**を追加する段階設計を推奨。

---

## 1. 評価メトリクス設計

### 1.1 SNS投稿品質メトリクス（6軸）

| # | メトリクス | 定義 | 評価方法 | X重み | IG重み |
|---|---|---|---|---|---|
| M1 | **トーン適合度** | 指定トーン（やわらかい/ビジネス/カジュアル）への一致度 | LLM-as-Judge (1-5) | 0.20 | 0.25 |
| M2 | **情報正確性** | 元資料の事実を正しく反映しているか | LLM-as-Judge + 資料照合 (1-5) | 0.25 | 0.25 |
| M3 | **エンゲージメント期待度** | 読者がアクション（いいね/RT/保存）したくなるか | LLM-as-Judge (1-5) | 0.20 | 0.15 |
| M4 | **文字数適合度** | プラットフォーム制限・推奨範囲への収まり | ルールベース (0 or 1) | 0.10 | 0.10 |
| M5 | **NGルール遵守** | 禁止表現・必須要素のチェック | ルールベース + LLM (0 or 1) | 0.15 | 0.15 |
| M6 | **日本語自然さ** | 不自然な表現・機械的な言い回しがないか | LLM-as-Judge (1-5) | 0.10 | 0.10 |

### 1.2 媒体別の追加メトリクス

**X専用:**

| メトリクス | 定義 | 基準 |
|---|---|---|
| ハッシュタグ品質 | 発見されやすいタグを使用しているか | 3-5個、関連性あり |
| 導入インパクト | 最初の1行で興味を引けるか | LLM-as-Judge (1-5) |
| スレッド適性 | 単独ツイートとして完結しているか | Binary |

**Instagram専用:**

| メトリクス | 定義 | 基準 |
|---|---|---|
| セクション構成 | ━━━等で適切に区切られているか | ルールベース |
| CTA有無 | LINE登録/note誘導等のCTAが含まれるか | ルールベース |
| ハッシュタグ数 | 10-15個の範囲か | ルールベース |
| 保存誘導力 | 「保存推奨」等の保存を促す要素 | LLM-as-Judge (1-5) |

### 1.3 総合スコア計算

```python
def calculate_quality_score(metrics: dict, platform: str) -> float:
    """
    総合品質スコアを計算（0-100）
    NGルール違反 or 文字数超過 → 即座に不合格（スコア0）
    """
    # ハードフェイル: NGルール違反 or 文字数超過
    if metrics['ng_compliance'] == 0 or metrics['char_count_ok'] == 0:
        return 0.0

    weights = PLATFORM_WEIGHTS[platform]  # X or IG の重み配列
    
    # LLM評価メトリクス（1-5 → 0-100に正規化）
    weighted_sum = sum(
        (metrics[key] / 5.0) * weights[key]
        for key in ['tone', 'accuracy', 'engagement', 'naturalness']
    )
    
    return round(weighted_sum * 100, 1)
```

---

## 2. 評価データセット

### 2.1 ゴールドスタンダード構成

| カテゴリ | 件数 | 内容 |
|---|---|---|
| X 高品質サンプル | 30件 | 実際に高エンゲージメントだった投稿 or 圭一郎さん承認済み |
| X 低品質サンプル | 15件 | 典型的な問題パターン（NG表現、トーン不適合等） |
| IG 高品質サンプル | 30件 | 承認済み + エンゲージメント上位 |
| IG 低品質サンプル | 15件 | 典型的な問題パターン |
| NGルール違反サンプル | 20件 | 薬機法・景表法違反パターン（意図的に作成） |
| 境界ケース | 10件 | 判断が難しいグレーゾーン |
| **合計** | **120件** | |

### 2.2 アノテーション方法

```yaml
# 評価データセットのフォーマット
evaluation_set:
  - id: "eval_001"
    platform: "x"
    source_material: "自然音の周波数帯と副交感神経への影響に関する研究"
    generated_text: "自然音、聴いてますか？\n\n実は低い音ほど体がゆるむんです..."
    prompt_version: "v1.2"
    model: "claude-sonnet-4-20250514"
    
    # 人間評価（圭一郎さん or 担当者）
    human_scores:
      tone: 4          # やわらかさ ○
      accuracy: 5      # 事実正確 ○
      engagement: 4    # 興味を引く ○
      naturalness: 5   # 自然な日本語 ○
      overall: 4       # 総合
    human_comment: "良い。最後のCTAをもう少し自然に"
    
    # NGチェック結果
    ng_violations: []
    char_count: 178
    char_limit: 280
    
    # 期待される総合スコア
    expected_score_range: [75, 90]
```

### 2.3 データセット構築手順

1. **既存投稿の収集**: 過去のX/IG投稿から圭一郎さん承認済みのものを50件抽出
2. **人間アノテーション**: 6軸スコアを手動で付与（圭一郎さん + 1名のダブルチェック推奨）
3. **NG違反サンプル生成**: 意図的にNG表現を含む投稿を作成（テスト用）
4. **境界ケース追加**: 「効果が期待できます」等のグレーゾーン表現
5. **定期更新**: 月1回、新規承認投稿を10件追加

---

## 3. LLM-as-a-Judge 評価設計

### 3.1 評価プロンプト（トーン適合度）

```yaml
# prompts/eval/tone_judge.yaml
system: |
  あなたはSNS投稿の品質評価の専門家です。
  以下の基準に基づいて、投稿テキストのトーン適合度を1-5で評価してください。

  ## 評価基準
  - 5: 指定トーンに完全に一致。読者に自然に伝わる
  - 4: おおむね一致。軽微な調整で完璧になる
  - 3: 部分的に一致。いくつかの文がトーンから外れている
  - 2: トーンの不一致が目立つ。大幅な修正が必要
  - 1: 指定トーンと真逆、または機械的で不自然

  ## 評価手順
  まず以下のステップで分析し、最後にスコアを出力してください:
  1. 指定トーンの特徴を列挙する
  2. テキスト内の各文がトーンに合っているか確認する
  3. 全体的な印象を述べる
  4. スコアを決定する

  ## 出力形式
  ```json
  {
    "reasoning": "ステップ1-3の分析",
    "score": 4,
    "improvement_suggestion": "改善提案（あれば）"
  }
  ```

user: |
  ## 評価対象
  - プラットフォーム: {platform}
  - 指定トーン: {tone}
  - トーン説明: {tone_description}

  ## 投稿テキスト
  {generated_text}

  上記の投稿テキストのトーン適合度を評価してください。
```

### 3.2 評価プロンプト（情報正確性）

```yaml
# prompts/eval/accuracy_judge.yaml
system: |
  あなたはファクトチェックの専門家です。
  元の資料と生成された投稿テキストを比較し、情報の正確性を1-5で評価してください。

  ## 評価基準
  - 5: 元資料の情報を正確に反映。誇張や歪曲なし
  - 4: おおむね正確。軽微な簡略化があるが誤りではない
  - 3: 概ね正確だが、一部に不正確な表現や過度の簡略化がある
  - 2: 重要な事実の誤りや誤解を招く表現がある
  - 1: 元資料の内容と大きく異なる、または捏造された情報がある

  ## 特に注意すべき点
  - 数値データの正確性（年号、割合、人数等）
  - 因果関係の正確性（「AだからB」の論理）
  - 効果に関する断言（薬機法リスク）
  - 元資料にない情報の追加（ハルシネーション）

  ## 出力形式
  ```json
  {
    "reasoning": "照合結果の詳細",
    "score": 4,
    "inaccuracies": ["不正確な点があれば列挙"],
    "hallucinations": ["元資料にない追加情報があれば列挙"]
  }
  ```

user: |
  ## 元資料
  {source_material}

  ## 生成された投稿テキスト
  - プラットフォーム: {platform}
  - テキスト: {generated_text}

  情報の正確性を評価してください。
```

### 3.3 バイアス対策

```python
class LLMJudge:
    """LLM-as-a-Judgeラッパー（バイアス対策込み）"""

    async def evaluate(self, text: str, criteria: str, **kwargs) -> dict:
        # 1. 2回評価して一貫性チェック（位置バイアス対策）
        score_1 = await self._single_eval(text, criteria, **kwargs)
        score_2 = await self._single_eval(text, criteria, **kwargs)

        # 2. スコア差が2以上なら3回目で決定
        if abs(score_1['score'] - score_2['score']) >= 2:
            score_3 = await self._single_eval(text, criteria, **kwargs)
            scores = [score_1['score'], score_2['score'], score_3['score']]
            final_score = sorted(scores)[1]  # 中央値
        else:
            final_score = round((score_1['score'] + score_2['score']) / 2, 1)

        return {
            'score': final_score,
            'reasoning': score_1['reasoning'],  # 初回の推論を採用
            'consistency': abs(score_1['score'] - score_2['score']) <= 1,
        }

    async def _single_eval(self, text, criteria, **kwargs):
        # CoT: スコアの前に推論を出力させる（バイアス低減）
        response = await self.llm.generate(
            system=self.eval_prompts[criteria],
            user=self._format_user_prompt(text, **kwargs),
            response_format={"type": "json_object"},
        )
        return json.loads(response)
```

---

## 4. NGルール自動チェック

### 4.1 アーキテクチャ: 3層ハイブリッド

```
投稿テキスト
     │
     ▼
┌─────────────────────────┐
│ Layer 1: ルールベース    │  ← 高速・確実（<10ms）
│  - 正規表現マッチ       │
│  - 文字数チェック       │
│  - 必須要素チェック     │
└────────┬────────────────┘
         │ Pass
         ▼
┌─────────────────────────┐
│ Layer 2: 辞書+パターン   │  ← 中速・高精度（<100ms）
│  - 薬機法NGワード辞書   │
│  - 景表法表現パターン   │
│  - 類義語展開マッチ     │
└────────┬────────────────┘
         │ Pass
         ▼
┌─────────────────────────┐
│ Layer 3: LLM判定        │  ← 低速・文脈理解（<3s）
│  - グレーゾーン判定     │
│  - 文脈依存のNG検知     │
│  - 暗示的表現の検出     │
└────────┬────────────────┘
         │
         ▼
     結果（Pass / Fail + 理由）
```

### 4.2 Layer 1: ルールベース実装

```python
import re
from dataclasses import dataclass

@dataclass
class NgRule:
    id: str
    name: str
    check_type: str  # 'forbidden' | 'required' | 'format' | 'char_count'
    patterns: list[str] = None
    regex: str = None
    required_elements: list[str] = None
    char_min: int = None
    char_max: int = None

class RuleBasedChecker:
    def __init__(self, rules: list[NgRule]):
        self.rules = rules
        # 正規表現のプリコンパイル
        self._compiled = {
            r.id: re.compile(r.regex) for r in rules if r.regex
        }

    def check(self, text: str, platform: str) -> list[dict]:
        violations = []

        for rule in self.rules:
            if rule.check_type == 'forbidden':
                # 禁止パターンマッチ
                for pattern in (rule.patterns or []):
                    if pattern in text:
                        violations.append({
                            'rule_id': rule.id,
                            'type': 'forbidden',
                            'matched': pattern,
                            'suggestion': rule.replacement_hint,
                        })

            elif rule.check_type == 'format':
                # 正規表現フォーマットチェック
                if rule.id in self._compiled:
                    matches = self._compiled[rule.id].findall(text)
                    if matches:
                        violations.append({
                            'rule_id': rule.id,
                            'type': 'format',
                            'matched': matches,
                        })

            elif rule.check_type == 'required':
                # 必須要素チェック
                for elem in (rule.required_elements or []):
                    if elem not in text:
                        violations.append({
                            'rule_id': rule.id,
                            'type': 'missing_required',
                            'missing': elem,
                        })

            elif rule.check_type == 'char_count':
                # 文字数チェック
                count = len(text) if platform != 'x' else self._weighted_count(text)
                if rule.char_max and count > rule.char_max:
                    violations.append({
                        'rule_id': rule.id,
                        'type': 'char_overflow',
                        'count': count,
                        'limit': rule.char_max,
                    })

        return violations

    def _weighted_count(self, text: str) -> int:
        """X（Twitter）の重み付き文字数カウント"""
        count = 0
        for char in text:
            if ord(char) > 0xFF:  # 全角
                count += 2
            else:
                count += 1
        return count
```

### 4.3 Layer 2: 薬機法NGワード辞書

```yaml
# data/ng_dictionaries/yakuji_law.yaml
version: "1.0"
updated: "2026-04-16"

# 完全一致NG
exact_forbidden:
  - "効果があります"
  - "治ります"
  - "改善します"
  - "治癒"
  - "治療"
  - "医学的に証明"
  - "科学的に実証"
  - "必ず効く"
  - "万能"

# パターンNG（正規表現）
pattern_forbidden:
  - pattern: "(癌|がん|ガン).*(治|消|なくな)"
    description: "がん治療を暗示"
  - pattern: "(病気|疾患|症状).*(治す|改善|解消)"
    description: "疾患治療を暗示"
  - pattern: "(必ず|絶対|100%).*(効果|効く|改善)"
    description: "効果の断言"
  - pattern: "(医師|医者|専門家).*(推薦|推奨|お墨付き)"
    description: "医療専門家の推薦を暗示"

# 言い換え推奨
soft_alternatives:
  "効果があります": "〜と感じる方もいます"
  "改善します": "〜のサポートとして"
  "科学的に証明": "研究で報告されています"
  "治ります": "心地よさを感じていただけます"

# グレーゾーン（Layer 3 LLM判定に委任）
gray_zone:
  - "期待できます"
  - "効果的"
  - "有効"
  - "実感"
  - "体験者の声"
```

### 4.4 Layer 3: LLM判定（グレーゾーン）

```yaml
# prompts/eval/ng_check_llm.yaml
system: |
  あなたは日本の薬機法・景表法に詳しい広告審査の専門家です。
  SNS投稿テキストに法令違反または違反のリスクがある表現がないかチェックしてください。

  ## チェック観点
  1. **薬機法**: 医薬品・医療機器でないものに治療効果を暗示していないか
  2. **景表法**: 優良誤認・有利誤認を招く表現がないか
  3. **暗示的表現**: 直接断言していなくても、文脈上効果を保証しているように読めないか
  4. **体験談の使い方**: 個人の体験を一般化していないか

  ## 判定基準
  - SAFE: 問題なし
  - CAUTION: グレーゾーン（修正推奨だが掲載可能）
  - VIOLATION: 明確な違反（修正必須）

  ## 出力形式
  ```json
  {
    "overall": "SAFE" | "CAUTION" | "VIOLATION",
    "findings": [
      {
        "text_excerpt": "問題のある箇所",
        "issue": "問題の説明",
        "severity": "CAUTION" | "VIOLATION",
        "suggestion": "修正案"
      }
    ],
    "reasoning": "判断理由"
  }
  ```
```

---

## 5. プロンプトバージョニング + トレーサビリティ

### 5.1 データモデル追加

```sql
-- プロンプトバージョン管理テーブル
CREATE TABLE public.prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_key VARCHAR(100) NOT NULL,     -- 'x_post', 'ig_post', 'eval_tone' 等
  version VARCHAR(20) NOT NULL,          -- 'v1.0', 'v1.1', 'v2.0'
  content TEXT NOT NULL,                 -- プロンプト全文
  variables JSONB,                       -- 使用する変数一覧
  model VARCHAR(50) NOT NULL,            -- 'claude-sonnet-4-20250514', 'gpt-4o'
  is_active BOOLEAN DEFAULT false,       -- 現在有効なバージョン
  created_at TIMESTAMPTZ DEFAULT now(),
  created_by UUID REFERENCES auth.users(id),
  UNIQUE (prompt_key, version)
);

-- 投稿テーブルにprompt_version_idを追加
ALTER TABLE public.posts ADD COLUMN prompt_version_id UUID REFERENCES public.prompt_versions(id);

-- 評価ログテーブル
CREATE TABLE public.eval_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID REFERENCES public.posts(id),
  prompt_version_id UUID REFERENCES public.prompt_versions(id),
  eval_type VARCHAR(50) NOT NULL,       -- 'tone', 'accuracy', 'ng_check' 等
  model_used VARCHAR(50) NOT NULL,       -- 評価に使ったモデル
  scores JSONB NOT NULL,                 -- 各メトリクスのスコア
  total_score FLOAT,
  reasoning TEXT,
  ng_violations JSONB,
  tokens_used INT,
  cost_usd FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.2 トレーサビリティフロー

```
資料アップロード
  ↓
GenerationJob作成
  ↓
prompt_versions から active プロンプトを取得
  ↓
LLM API呼び出し（model + prompt_version記録）
  ↓
Post作成（prompt_version_id をセット）
  ↓
自動評価パイプライン実行
  ↓
eval_logs に結果を記録
  ↓
ダッシュボードで prompt_version 別の品質推移を可視化
```

---

## 6. ABテスト基盤

### 6.1 オフラインABテスト（Phase 1）

```python
class PromptABTest:
    """プロンプトバージョン間のオフライン比較"""

    def __init__(self, eval_dataset: list[dict], judge: LLMJudge):
        self.dataset = eval_dataset
        self.judge = judge

    async def run(
        self,
        prompt_a_id: str,
        prompt_b_id: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> dict:
        results_a = []
        results_b = []

        for sample in self.dataset:
            # 同じ資料から両方のプロンプトで生成
            text_a = await generate(sample['source'], prompt_a_id, model)
            text_b = await generate(sample['source'], prompt_b_id, model)

            # 同じ評価基準でスコアリング
            score_a = await self.judge.evaluate_all(text_a, sample['platform'])
            score_b = await self.judge.evaluate_all(text_b, sample['platform'])

            results_a.append(score_a)
            results_b.append(score_b)

        return {
            'prompt_a': {
                'id': prompt_a_id,
                'avg_score': mean([r['total'] for r in results_a]),
                'ng_violation_rate': self._violation_rate(results_a),
                'scores_by_metric': self._aggregate_by_metric(results_a),
            },
            'prompt_b': {
                'id': prompt_b_id,
                'avg_score': mean([r['total'] for r in results_b]),
                'ng_violation_rate': self._violation_rate(results_b),
                'scores_by_metric': self._aggregate_by_metric(results_b),
            },
            'winner': 'a' if mean_a > mean_b else 'b',
            'statistical_significance': self._calc_significance(results_a, results_b),
            'sample_size': len(self.dataset),
        }
```

### 6.2 オンラインABテスト（Phase 2）

```python
# Phase 2: 実際のエンゲージメント指標との相関

# 投稿テーブルに追加
# ALTER TABLE posts ADD COLUMN ab_group VARCHAR(1) CHECK (ab_group IN ('A', 'B'));

class OnlineABTracker:
    """投稿後のエンゲージメント指標を追跡"""

    metrics = [
        'likes',           # いいね数
        'retweets',        # RT/リポスト数
        'replies',         # リプライ数
        'impressions',     # インプレッション
        'saves',           # 保存数（IG）
        'profile_visits',  # プロフィール訪問
        'link_clicks',     # リンククリック
    ]

    async def collect_engagement(self, post_id: str, hours_after: int = 48):
        """投稿後48時間のエンゲージメント指標を収集"""
        # X API / IG Insights APIからデータ取得
        pass

    def correlate_with_eval_scores(self, ab_results: dict) -> dict:
        """評価スコアとエンゲージメントの相関を分析"""
        # LLM評価スコアが高い投稿は実際にエンゲージメントも高いか？
        pass
```

---

## 7. 評価パイプライン設計

### 7.1 パイプラインフロー

```
AI記事生成リクエスト
  │
  ├── 1. LLMで投稿テキスト生成（Claude or OpenAI）
  │
  ├── 2. NGチェック（Layer 1-3）
  │     ├── VIOLATION → 自動再生成（最大2回）
  │     ├── CAUTION → フラグ付きで通過
  │     └── SAFE → 通過
  │
  ├── 3. 品質評価（LLM-as-Judge, 6軸）
  │     ├── スコア < 60 → 自動再生成（最大2回）
  │     ├── スコア 60-75 → 「要確認」フラグ
  │     └── スコア > 75 → 合格
  │
  ├── 4. eval_logs に記録
  │
  └── 5. 結果をユーザーに返却（スコア + 改善提案付き）
```

### 7.2 Celeryタスク実装

```python
@celery_app.task
def evaluate_generated_post(post_id: str):
    """生成された投稿の品質を自動評価"""
    post = get_post(post_id)

    # Layer 1-2: ルールベースNGチェック（高速）
    rule_violations = rule_checker.check(post.text, post.platform)
    
    # Layer 3: LLM NGチェック（グレーゾーンのみ）
    if has_gray_zone_patterns(post.text):
        llm_ng_result = llm_ng_checker.check(post.text)
    else:
        llm_ng_result = {'overall': 'SAFE', 'findings': []}

    # LLM-as-Judge 品質評価
    eval_scores = {}
    for metric in ['tone', 'accuracy', 'engagement', 'naturalness']:
        eval_scores[metric] = llm_judge.evaluate(
            post.text, metric,
            platform=post.platform,
            tone=post.tone_setting,
            source=post.source_material,
        )

    # 総合スコア
    total = calculate_quality_score(eval_scores, post.platform)

    # eval_logs に記録
    save_eval_log(post_id, eval_scores, total, rule_violations, llm_ng_result)

    return {
        'total_score': total,
        'metrics': eval_scores,
        'ng_violations': rule_violations,
        'llm_ng_check': llm_ng_result,
    }
```

---

## 8. コスト試算

### 8.1 評価パイプラインのコスト

| 処理 | モデル | 入力トークン | 出力トークン | 単価 | 1投稿あたり |
|---|---|---|---|---|---|
| トーン評価 | Claude Sonnet | ~800 | ~200 | $3/$15 per M | ~$0.005 |
| 正確性評価 | Claude Sonnet | ~1,500 | ~300 | $3/$15 per M | ~$0.009 |
| エンゲージメント評価 | Claude Sonnet | ~800 | ~200 | $3/$15 per M | ~$0.005 |
| 日本語自然さ評価 | Claude Sonnet | ~800 | ~200 | $3/$15 per M | ~$0.005 |
| NGチェック(LLM) | Claude Sonnet | ~1,000 | ~300 | $3/$15 per M | ~$0.008 |
| **合計** | | | | | **~$0.032/投稿** |

### 8.2 月間コスト試算

| シナリオ | 投稿数/月 | 評価コスト | 生成コスト | 合計 |
|---|---|---|---|---|
| Phase 1（自社運用） | 60件 | $1.92 | $3.60 | ~$5.52 |
| Phase 2（10ユーザー） | 600件 | $19.20 | $36.00 | ~$55.20 |
| Phase 3（100ユーザー） | 6,000件 | $192.00 | $360.00 | ~$552.00 |

### 8.3 コスト削減戦略

| 戦略 | 削減率 | トレードオフ |
|---|---|---|
| NGチェックLayer 1-2で完結するものはLLM判定をスキップ | ~30% | なし（Layer 1-2で十分な場合のみ） |
| 評価の一貫性チェック（2回→1回）をスコア安定時にスキップ | ~40% | 品質が安定した後のみ適用 |
| Haiku/GPT-4o-miniで事前スクリーニング、Sonnetは閾値付近のみ | ~50% | 微妙なケースの判定精度が下がる可能性 |
| バッチ評価（複数投稿を1リクエストにまとめる） | ~20% | レイテンシ増加 |

---

## 9. ダッシュボード（品質モニタリング）

### 9.1 表示項目

```
┌──────────────────────────────────────────────────┐
│  📊 品質ダッシュボード          [今週] [今月] [全期間] │
│                                                    │
│  ┌─ 総合品質スコア推移 ───────────────────────┐   │
│  │  100 ┤                                      │   │
│  │   80 ┤     ╭──╮  ╭───╮  ╭──────            │   │
│  │   60 ┤  ╭──╯  ╰──╯   ╰──╯                  │   │
│  │   40 ┤──╯                                   │   │
│  │   20 ┤                                      │   │
│  │    0 ┼──┬──┬──┬──┬──┬──┬──┬──              │   │
│  │      4/1  4/5  4/9  4/13                     │   │
│  │      ─── X  ─── IG                          │   │
│  └─────────────────────────────────────────────┘   │
│                                                    │
│  ┌─ プロンプトバージョン比較 ──────────────────┐   │
│  │  v1.2 (現行): 平均 78.5   NGrate: 2%        │   │
│  │  v1.1 (前回): 平均 72.3   NGrate: 5%        │   │
│  │  改善: +6.2pt  NG率: -3pt                   │   │
│  └─────────────────────────────────────────────┘   │
│                                                    │
│  ┌─ NG違反トップ5 ────────────────────────────┐   │
│  │  1. 効果断言（薬機法） ████████  8件          │   │
│  │  2. 改行前句読点      ████      4件          │   │
│  │  3. ハッシュタグ不足   ███       3件          │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

---

## 10. 優先アクション

| # | アクション | 理由 | 工数 |
|---|---|---|---|
| 1 | 評価データセット構築（既存承認投稿50件 + NG20件） | 全ての評価の基盤 | 3日 |
| 2 | Layer 1-2 NGルールチェッカー実装 | 即効性が高く、生成品質を底上げ | 2日 |
| 3 | LLM-as-Judge プロンプト4種作成 + 人間評価との相関検証 | 自動評価の信頼性を確立 | 3日 |
| 4 | prompt_versions + eval_logs テーブル作成 | トレーサビリティの基盤 | 1日 |
| 5 | 評価パイプラインCeleryタスク実装 | 生成→評価の自動フロー | 2日 |
| 6 | 品質ダッシュボード（簡易版） | 品質の可視化・監視 | 3日 |

---

## 11. 未決定事項

| 項目 | 選択肢 | 決定時期 |
|---|---|---|
| 評価モデル | Claude Sonnet vs GPT-4o vs 両方 | データセット構築後に相関検証して決定 |
| 人間評価の頻度 | 毎週 vs 毎月 vs プロンプト更新時のみ | 運用開始1ヶ月後に判断 |
| 自動再生成の閾値 | スコア60 vs 50 vs 70 | データセット構築後にチューニング |
| エンゲージメント指標収集 | Phase 2以降 | Phase 1の品質が安定してから |
