# knowledge/ — SNS記事の根拠となる知識層

SNS記事の事実誤りを減らすための知識層。
**「要約を保存する」のをやめ、原文と条件をそのまま保持し、承認済みのものだけ記事に使う**方式。

## なぜこの構造か

圭一郎さんの修正が毎回発生し、その内容が会話の中で消えて資産化されていなかった。
原本398ファイルを要約した `資料まとめ.md` には出典ページがなく、記事作成時に検証できなかった。

過去の修正実データを分析した結果、**壊れているのは数字そのものより文脈**だった
（対象者が誰か・何分か・比較群があるか・相関か因果か・どこまで一般化してよいか）。
そのため Evidence カードは数値だけでなく研究デザインを分離して保持する。

## ディレクトリ

```
knowledge/
├── README.md          このファイル
├── taxonomy.md        修正種別の分類軸と出典の権威レベル
├── schema.md          カードのスキーマ定義
├── escalation.md      原本と圭一郎さんの指示が食い違う案件
├── verify_cards.py    カードの機械検証
├── evidence/          EV-xxxx: 原文と実験条件（不変）
│   └── INDEX.md       カード一覧
├── claims/            AC-xxxx: 発信してよい主張（圭一郎さん承認後）
├── editorial/         RULE-xxxx: 表現・ブランドの恒久ルール
├── campaign/          CMP-xxxx: 今回限りの判断
└── _extract/          原本PDFの抽出テキスト（gitignore・中間生成物）
```

## 鉄則

1. **`verbatim` は原文を一字も変えない。** 誤字も残す。要約は別フィールド。
2. **有意差がなかった項目も必ず記録する。** 落とすと過大解釈になる。
3. **`generalization_ng` が空のカードは使用不可。** 一般化範囲を書けないカードは未完成。
4. **`approval` が3つとも「済」でなければ記事生成に使えない。**
   （転記＝原文照合／解釈＝科学的に妥当か／公開＝広報として出してよいか）
5. **記事の編集差分から Evidence カードを自動更新してはいけない。**
   修正には事実・解釈・表現・好み・今回限りの判断が混在する。必ず分類と承認を経る。
6. **「自然音の聴取」と「体感音響（振動刺激）」は別の介入。** 混同禁止。

## 使い方

### 原本からテキストを抽出する

```bash
pdftotext -layout "資料_分類済み/学術論文 学会発表/○○.pdf" "knowledge/_extract/○○.txt"
```

> 2段組PDFは左右の列が同じ行に混ざって出力される。カード作成時は列を解きほぐすこと。
> 画像のみのPDF（`2000日本健康科学学会第16回学術大会` 等3件）はテキスト抽出できず、OCRが必要。

### カードを検証する

```bash
python3 knowledge/verify_cards.py
```

検出するもの:
- 原文に存在しない数値の混入（捏造検出）
- 原文が「変化なし」と述べているのに `significant: false` がない（取りこぼし検出）
- `generalization_ng` の未記入
- 未承認なのに `status: active`
- `source_file` の参照切れ

### レビューシートを更新する

```bash
/usr/bin/python3 create_review_sheet.py
```

`knowledge/evidence/` の内容を Google スプレッドシートの「週次_カード承認」タブへ反映する。
冪等（何度実行してもよい）。**承認欄の記入内容も消えるため、承認後は先に下の取り込みを行うこと。**

### 承認結果をカードに取り込む

```bash
/usr/bin/python3 sync_approvals.py           # 差分の確認だけ（ドライラン）
/usr/bin/python3 sync_approvals.py --apply   # カードに書き込む
```

スプレッドシートで記入された承認結果を `approval` / `status` / レビューコメントに反映する。
- シートに書かれた内容しか反映しない（自動承認はしない）
- `disputed` のカードは触らない
- コメントは上書きせず追記する（判断の履歴を残す）
- 解釈・公開の両方が「済」になったカードだけ `status: active` に上がり、記事生成に使えるようになる

> homebrew の python3.14 は pyexpat が壊れており gspread が動かない。`/usr/bin/python3` を使うこと。
> サービスアカウントは Drive 容量を持たないため新規スプレッドシートを作成できない。
> 既存の「SNS投稿管理シート」にタブを追加する方式にしている。

## 週次ループを回す

```bash
/usr/bin/python3 run_weekly_loop.py                 # 通常（承認済みカードのみ使用）
/usr/bin/python3 run_weekly_loop.py --test-cards    # 未承認カードも使う（ループ検証用）
/usr/bin/python3 run_weekly_loop.py --no-write      # シートに書かず結果だけ表示
```

①収集 → ②企画・執筆（`claude -p`）→ ③検証 → ④`週次_レビュー` へ投入。
承認済みカードが0枚のときは何も生成せず停止する。

### 投稿されないことの保証（三重）

1. 書き込み先は `週次_レビュー` タブ。投稿を行う `x_auto_poster.py` / `ig_auto_poster.py` が
   読むのは `X投稿キュー` / `IG投稿キュー` タブのみ
2. 書き込むステータスは `AI下書き` / `要確認あり`。投稿トリガーは `投稿予約` のみ
3. `run_weekly_loop.py` は X / Instagram の API を import すらしていない

投稿するには人が内容を確認し、投稿キューへ移した上でステータスを `投稿予約` にする必要がある。

### 定期実行

> ⚠️ **プロジェクトは `~/Desktop` 配下にあり、macOS の TCC（プライバシー保護）により
> launchd から起動されたプロセスはここのファイルを開けない**（`Errno 1: Operation not permitted`）。
> そのため保護対象外の `~/joyfoundation-loop-runtime/` にコピーを置いて実行する。
> 既存の `~/sns-poster-runtime/`（自動投稿）と同じ方式。

```bash
./sync_loop_runtime.sh                                        # 実行用コピーを更新
cp com.joyfoundation.weekly-loop.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.joyfoundation.weekly-loop.plist
launchctl start com.joyfoundation.weekly-loop                 # 即時実行して動作確認
launchctl unload ~/Library/LaunchAgents/com.joyfoundation.weekly-loop.plist  # 停止
```

**`./sync_loop_runtime.sh` を実行し忘れると、承認したカードが反映されない。**
以下のあとは必ず実行すること。

- `run_weekly_loop.py` を変更したとき
- `sync_approvals.py --apply` でカードを承認したあと
- 表現ルール・用語集を変更したとき

同期が3日以上前だとループ実行時に警告が出る。

検証期間中は毎日9:00。本番では plist の `StartCalendarInterval` に `Weekday` を足して週1にし、
`--test-cards` を外すこと。

### 本番運用の想定（週次）

```
金曜 9:00   生成（翌週分・3本）
土日        圭一郎さんレビュー（週次_レビュー タブ）
月曜        承認分を X投稿キュー へ移し「投稿予約」にする
月〜日      予約時刻に自動投稿（既存の15分毎ポスターが実行）
```

まず週3本で「レビュー所要時間」と「修正率」を計測し、実測してから本数を増やす。
一度に5〜7本を完成稿で渡すと、後半ほどレビュー品質が落ちるため。

## 現在の状態（2026-07-28）

| 項目 | 状態 |
|------|------|
| Evidence カード | 12枚（EV-0001〜EV-0012） |
| 転記承認 | 12/12 済 |
| 解釈・公開承認 | 0/12 — **圭一郎さんのレビュー待ち** |
| 記事に使えるカード | **0枚**（承認が未のため） |
| エスカレーション | 1件未解決（ESC-001） |

Approved claim / Editorial rule / Campaign のカードは、圭一郎さんのレビュー後に作成する。
