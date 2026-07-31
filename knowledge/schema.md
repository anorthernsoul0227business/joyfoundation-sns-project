# 知識層スキーマ定義

## 設計原則

1. **知識を4層に分ける。1つのカードに詰めない。**
   表現ルールと学術事実を同じフィールドに混ぜると、早期に矛盾だらけになる。
2. **原文（verbatim）は加工しない。** 要約は別フィールド。
3. **数値だけでなく文脈を保持する。** 対象・介入・比較・指標・期間・因果性・一般化範囲。
   実データ上、壊れるのは数字そのものより文脈だった。
4. **承認は3段階に分ける。** 「圭一郎確認済」だけでは粗すぎる。

---

## 層の構成

| 層 | ID接頭辞 | 中身 | 可変性 |
|----|---------|------|--------|
| **Evidence** | `EV-` | 原文と実験条件。何が測られたか | 不変（原本が変わらない限り） |
| **Approved claim** | `AC-` | SNSで発信してよい主張 | 圭一郎さん承認で確定 |
| **Editorial rule** | `RULE-` | 表現・ブランドの恒久ルール | 追記型 |
| **Campaign decision** | `CMP-` | 今回限りの判断 | 期限付き |

---

## Evidence カード（`knowledge/evidence/EV-XXXX.md`）

```yaml
---
id: EV-0001
title: 短い識別名（内容ではなく識別用）

# --- 出典 ---
source_file: 資料_分類済み/学術論文 学会発表/○○.pdf
source_page: p.1              # 不明なら null
source_type: 査読論文 | 学会抄録 | 紀要 | 自社報告 | 解説記事 | 一般記事
authority_level: L1           # taxonomy.md 参照
published: 2018-12            # 発表年月
venue: 第83回日本温泉気候物理医学会

# --- 研究デザイン（Codex指摘により必須化）---
subjects: 男子学生7名、平均年齢23.0±3.3歳   # 対象者。属性を省略しない
n: 7
intervention: 自然音を10分間聴取（屋久島のせせらぎ＋ハワイ・カウアイ島のせせらぎと滝、早朝収録）
comparator: 自然音を聴かない対照群           # なし=null
measures: [オキシトシン濃度, コルチゾール濃度, 心拍変動, STAI]
timing: 安静坐位20分後(Pre)→介入10分→介入後20分(Post)
design: 群間比較 | 同一被験者内比較 | 単群前後比較 | 観察研究
causality: 介入研究 | 相関 | 事例報告   # 因果を主張できるか

# --- 結果（原文のまま。要約しない）---
verbatim: |
  （原文をそのまま転記。改変禁止）
findings:
  - metric: オキシトシン
    result: 増加
    value: "Pre 1.4±0.4 ng/mL → Post 2.0±0.6 ng/mL"
    p: "0.01"
    significant: true
  - metric: HF（心拍変動）
    result: 変化なし
    value: null
    p: null
    significant: false        # ← 有意差なしも必ず記録する

# --- 制約（これが最重要）---
limitations: |
  原文に書かれた限界をそのまま転記。
  例: 「同一被験者内での比較のため、音を聞かせること単体の効果は明らかになっていない」
generalization_ng: |
  この結果から言ってはいけないこと。
  例: 対象は男子学生7名のみ。女性・高齢者・患者への一般化不可。
  例: 「自然音」の研究であり「体感音響」の結果ではない。

# --- 承認（3段階に分離）---
approval:
  transcription: 未 | 済     # 原文転記が正しいか（担当: 開発側で照合可能）
  interpretation: 未 | 済    # 科学的解釈として妥当か（担当: 圭一郎さん）
  publication: 未 | 済       # 広報表現として出してよいか（担当: 圭一郎さん）
approved_at: null
reviewer: null

# --- 運用 ---
topics: [自律神経, ストレス, 睡眠, オキシトシン]
status: draft | active | disputed | retired
version: 1
---

## 補足
自由記述。取り違えやすい点、関連カードへのリンクなど。
```

### 必須ルール

- **`significant: false` の項目も必ず書く。** 有意差がなかった事実を落とすと過大解釈が生まれる。
- **`generalization_ng` が空のカードは使用不可。** 一般化範囲を書けないカードは未完成。
- **`approval` が3つとも「済」でなければ記事生成に使えない。**

---

## Approved claim カード（`knowledge/claims/AC-XXXX.md`）

Evidence をそのままSNSに書くことはできない。発信可能な言い回しを別途承認する。

```yaml
---
id: AC-0001
based_on: [EV-0001]           # 根拠となるEvidenceカード。複数可
claim_text: 自然音を10分間聴いた研究で、リラックスに関わるホルモンの変化が報告されています
forbidden_variants:           # この主張から作ってはいけない言い回し
  - 自然音にはストレスを下げる効果があります
  - 自然音を聴くと必ずリラックスできます
required_qualifier: 「〜という報告があります」の形を保つ。断定形不可
media: [X, Instagram, note]   # 使ってよい媒体
approval:
  interpretation: 済
  publication: 済
approved_at: 2026-07-28
reviewer: 喜田圭一郎
status: active
---
```

---

## Editorial rule カード（`knowledge/editorial/RULE-XXXX.md`）

```yaml
---
id: RULE-0001
category: X1                  # taxonomy.md の修正種別コード
rule: 「効果があります」「効果が確認されています」は使用しない
reason: 薬機法・景品表示法のリスク。および押し売り感が出る
alternatives:
  - 〜という報告があります
  - 〜と感じる方が多いです
  - 〜が期待されています
scope: 全媒体
source: 圭一郎さん 2026-03-11 メール
status: active
---
```

---

## Campaign decision カード（`knowledge/campaign/CMP-XXXX.md`）

```yaml
---
id: CMP-0001
subject: カンガルーカップ2026
decision: 体験勧誘ではなく活動紹介トーンで告知する
valid_until: 2026-05-31       # 期限を必ず切る
source: 圭一郎さん 2026-04-09
status: active
---
```

---

## 生成時の制約

記事生成エージェントに課す制約:

1. `approval` が全て「済」の Evidence / Approved claim のみ参照可
2. カードにない数値は生成禁止
3. `generalization_ng` に該当する記述は生成禁止
4. `RULE-` に抵触する表現は生成禁止
5. 各投稿に「使用カードID」「カード由来の文」「AIの解釈・CTA」「外部情報」を分離して出力
