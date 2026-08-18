# 開発ログ (DEVLOG)

## 2026-08-18（記事の質の作り直し ＋ Voice層の新設）

### 実施内容

**圭一郎さんへのレビュー依頼**

- 掲示板形式のレビューページを Artifact で作成（記事ごとにコメント欄・書き込みが即保存され双方に反映）
- 圭一郎さんは claude.ai のアカウントを持たないため、この方式は使えないと判明。
  編集者権限の付与は Team/Enterprise プランのみ、公開は内部資料なので不可
- メールに切り替え。1通目は `550 High probability of spam` で拒否された
  （Driveリンク6本＋健康関連語＋装飾記号の連続が原因と判断）。
  リンクとハッシュタグと罫線を落として再送し、到達
- 康二郎さんの意見を本文に載せ、記事ごとに返信欄を設けた形に作り直し

**記事の質に関する指摘の反映（康二郎さんのレビュー6件＋全体所見）**

生成記事39本を読み比べるページを作り、語彙の偏りを実測。
39本中27本が「10例中◯例」に触れ、「小さな」22回、「原文」21回。
そのうえで受けた指摘をルール化した。

- `RULE-0012` 書き直し — 限界を「限界」として書かず**伸びしろ**として書く
- `RULE-0013` 強化 — **主役は協会。書き手はその広報**（第三者として書かない）
- `RULE-0014` — CTA に「誰でもできる当たり前のこと」を書かない
- `RULE-0015` — 数値には**高い低いが判る基準**を添える
- `RULE-0016` — 結果を**解釈して提案に変える**。転記で終わらない
- `RULE-0017` — 体感音響は**物と動作**で説明（クッション・当てる・撫でる）
- `RULE-0018` — **起承転結**。「一記事一本の糸」（起と結が同じ物語であること）
- `RULE-0019` — **自然音の収録と体感音響は別の活動**。因果でつながない（事実誤りの指摘より）
- `RULE-0005` に追記 — 誘導そのものは禁じていない。着地が金銭だけになっていないかで判断

効果表現の線引きも確定した。**私たちが結論を言うのではなく、読み手が結論に至れる
ように材料を置く**（例:「緊張したときに増えるホルモンが減っていた」と書けば、
読者は自分で意味を受け取れる）。

**Voice カードの新設**

Evidence（学会発表11枚）だけで書くと毎回研究の話になり注釈が増える。
実績のある過去のIG投稿は思想・経験知が素材だった。その層を用意した。

- `knowledge/voice/` と schema を新設。逐語・出典・切り取り禁止事項を持つ
- `fetch_journal.py` で協会誌8号（vol.26-27〜39-40、計33,088字）を公式サイトから取得
- vol.37-38 と vol.39-40 から19枚を作成。**全19枚の逐語が原本と一致**することを機械照合
- 仕分け: 可16 / 要確認1 / 不可2
- `資料まとめ.md` は要約であり逐語ではないため、Voice の verbatim には使わない

**そのほか**

- Instagram の字数を 300〜500字 → **400〜600字**に変更（CLAUDE.md も更新）。
  読みやすさは長さではなく、主題を1本に絞ることと改行で作る
- タイトル【】必須、1行20〜25字、2〜3行ごとに空行を生成プロンプトに追加
- `verify()` が `EV-` しか見ておらず、Voice を使った記事が全て
  「存在しないカードID」と誤検出されていた不具合を修正

### 成果

- 生成記事が実際に変わった。研究の数値ゼロで、理事長の言葉を引き、
  起と結が同じ糸で通った Instagram 記事が出るようになった
- 材料: Evidence 11 / Voice 16 / Rule 19 / Image 225（使用可178）/ イベント 24

### 課題・備考

- **要確認カードは1枚ずつ諮らず、たまってからまとめて判断を仰ぐ**運用に決定
- VO-0016「音の振動が水分子の溶解力を高めることが実験により確かめられている」に
  対応する Evidence カードが無い。実験資料の所在を圭一郎さんに確認したい
- 「低い音→筋肉がゆるむ／高い音→意識がクリアに」（2026年5月のIG投稿）の根拠が不明。
  `EV-0011` には周波数データから効果を導くことを禁じる記述がある。要確認
- X の字数超過（140字上限に対し151〜152字）が3回続いている
- 協会誌は残り6号分が未カード化（約27,000字）
- 圭一郎さんからの返信待ち


## 2026-08-17（週次ループの障害3件を修正 ＋ イベント情報の正本化）

### 実施内容

**1. 13日間の稼働で見つかった障害の修正**

- **記事9本の取りこぼしを回収**: 8/13・8/14・8/15 の生成物がシート投入時の通信エラーで落ちていた。退避ファイルから `republish.py` で全件復旧
- **キルスイッチの誤作動を修正**（8/2 から時事文脈が死んでいた）
  - 原因: 収集結果の根拠文「特別警報の発表はなく…津波警報・噴火警戒レベル4以上の発表もなし」に検知語が並ぶため、単純な部分一致が**平常の説明を災害と誤読**していた
  - 対策: `kill_hits()` を新設。根拠文は句に割り、否定表現を伴う句を除外する。文脈アイテム側は従来どおり素朴に走査
  - 検証: 8パターンで両方向を確認（平常=不発動 / 特別警報・震度6・震度7・津波・解除後の被害継続・災害警戒中フラグ=発動）
- **原因が見えないバグを修正**: `claude` CLI は API エラーを stdout に書くため、stderr だけ見ていたログの理由が空だった。stdout も見るようにし、通信不良に対する再試行（15秒→30秒）を追加。タイムアウト・異常終了・JSON抽出失敗の3系統を拾う

**2. イベント情報の正本化**

- 共有カレンダーに圭一郎さんが 8/5 付で9〜10月の予定23件を登録してくださっていた（宿題分）
- `イベント予定` タブを新設し24件を登録（`create_event_sheet.py`）。列に**情報源**と**圭一郎さん確認**を持たせ、L1原本とL4カレンダーのどちらが根拠かを追えるようにした
- `load_events()` を改修: ISO形式の日付に対応（`parse_event_date()` を分離）、正本タブを優先、**時間・費用・申込先・補足**も記事プロンプトに渡す
- 空欄は空欄のまま渡す。埋まっていない項目を推測で補わせないため

### 成果

- 週次_レビュー: 36行（12日分 × 3媒体）。うち9本は今回の復旧分
- イベント24件のうち、**原本(L1)で裏が取れたのは4件**（ここちよい音の日 9/19・10/17、音のウェルビーイング 9/8・10/20）
- 原本PDFとカレンダーの照合が全項目一致（日付・曜日・「8月休み」）

### 課題・備考

- **通信の不安定さが根本原因**: シート投入失敗3件・収集失敗6件はすべてこのマシンの通信断。再試行で大半は吸収できるがコードでは根治できない
- **カレンダーのみが根拠のイベント20件**は未確認。特に以下を圭一郎さんに確認したい:
  - スターライトヒーリング マラマハワイが 9/5〜9/27 に**10公演**。費用・申込先が不明
  - **「食×音 太陽食品ここちよい音の日」(10/2・10/3) が長田整形外科の「ここちよい音の日」と同名で別会場**。読者が混同しうる
- 承認済みカードは依然 0枚（`--test-cards` で稼働中）
- 9/19 は33日先のため、ループが拾うのは 8/29 から（対象は21日以内）。範囲は広げない方針で確定

### 追記（夕方以降の作業）

**承認方式の変更（カード事前承認 → 完成投稿への承認）**

- `load_cards` から承認ゲートを撤去。`status: active` を要求せず、`disputed` のみ除外する
  - 承認 0/12 のまま数週間動かなかった。3者の壁打ちでも全員がこの設計に反対だった
- `extract_ac.py` を新設。圭一郎さんが `圭一郎OK` にした記事から Approved claim を切り出す
- 生成プロンプトに承認済みの言い回しを渡し、逐語で使われた場合のみ A 分級にする

ChatGPT・Fable 5 に最終確認を依頼し、**両者とも「設計変更は正しいが `--test-cards` を
今外すのは時期尚早」**と回答。理由は「圭一郎さんが39本を1本も見ていない状態で
本物の下書きを積んでも、未処理在庫が増えるだけ」。**launchd は変更していない。**

指摘を受けて修正した欠陥3件:

1. AC の承認元に `投稿予約`/`投稿済` を含めていた（運用ステータスなので本人未確認でも
   AC が作られる）→ `圭一郎OK` のみに限定
2. 修正版の全文を文単位で切り出していた（季節の挨拶まで AC になる）→ カード由来の
   主張文に限定し、修正版からは対応する文の言い回しだけを採る
3. **A分級が検証なしで通っていた**。AC をプロンプトに渡すだけで A を出しており、
   LLM が言い換えても素通りした → 逐語照合を追加。AC が0枚のときも A を出さない

**スプレッドシートの整理**

- 全14タブ・404行を `docs/sheet_backup_20260817/` に保存（サービスアカウントに
  Drive 容量がなくコピーは作れず）
- 表示5タブ（週次_レビュー / イベント予定 / X投稿キュー / IG投稿キュー / 画像フォルダ方針）、
  8タブを非表示、`週次_カード承認` を削除
- 削除したタブを参照する2スクリプトを処置。`sync_approvals.py` は退役、
  `create_review_sheet.py` は**実行するとタブが復活する**状態だったので生成を停止

**画像**

- `image_picker.py` を新設。使用回数と45日クールダウンで使い回しを防ぐ
- 索引に `場面` `場面種別` `汎用性` `食い違い` を追加。フォルダ名・ファイル名を
  Vision に文脈として渡す（圭一郎さんが人手で付けた情報を捨てていたため）
- 人物の一律ブロックを撤廃（RULE-0011）。止めるべきは人が写ることではなく
  場面と記事の食い違い
- 書影12枚を RULE-0008 で除外。データとロジックの両方で塞いだ
- 189枚を索引化。カード225枚、選定候補178枚（23枚から7.7倍）

**圭一郎さんへの初回レビュー案内**

- `docs/review_mail_20260817.md` を作成。39本から6本を選定（媒体2本ずつ・切り口重複なし・
  イベント告知1本）。全6本に画像を割り当て
- 送信は康二郎さんが行う

### 課題（追記分）

- **切り口の重複が実データで確認された**。同日生成の note 2本が「音は、体のどこで
  受け取るのか」「音を「体のどこ」で受け取るか」とほぼ同一。企画エージェントが要る
- 索引化で7枚が通信エラーで失敗（Space フォルダ）。再試行機構がない
- 旧カード36枚は `汎用性` が空欄（項目追加前に作成）
- R2 の公開URLが403。Instagram 投稿には公開URLが要る（X はローカルアップロードのため影響なし）


## 2026-08-04（ヘルシートラック初回クライアント打ち合わせ記録）

### 実施内容
- NotebookLM「Sound Healing for Driver Wellness and Safety」の新ソース（7/31 初回クライアント打ち合わせ録音の文字起こし）を全文確認
- 議事録を作成: `docs/healthy_truck_first_meeting_20260731.md`
- 要件定義書を v1.1 に更新: `docs/healthy_truck_requirements_v1.md`

### 成果（新事実）
- 車両: 2t車ほとんど・現行メーカーはトヨタといすゞ・夜間走行ほぼ無し・市街地中心
- ドライバー: ほぼ男性・20〜60代・平均40歳前後
- 運用方針確定: 運転中は自然音を常時再生（最低10分で自律神経に変化の実験知見）
- 効果測定候補が具体化: POMS（最簡便・3回測定）／心拍・血圧（安静5-10分必要）／唾液ホルモン（要即冷凍）／波動測定装置（先方が強く実施したい意向）
- クライアント理念: 「まず社員を健康に」「人を助けて我が身助かる」「1日1ギャグ」→ 現代表も日比氏
- まず研究所オフィス内での自然音再生からスタートする案。8/3リモート2h実施予定（済みの可能性）、8/21訪問時に音源持参予定

- 提案書 v2 を作成: `docs/healthy_truck_system_proposal_v2.md`
  - 3段構えに再構成: 第0段階=オフィス導入（8/21〜）→ 第1段階=トラック実証 → 第2段階=量産・組込み
  - 測定設計を具体化（POMS主指標・心拍血圧副指標・唾液オプション・波動測定併用）
  - クライアント理念に沿ったストーリーに変更
- 圭一郎さん送付用の統合PDF v2 を生成: `docs/ヘルシートラック要件・提案書_v2_20260804.pdf`（7/31新確定箇所は黄色マーカー表示）

### 課題・備考
- 文字起こしはASRベースのため固有名詞に誤認識あり（要確認箇所は議事録に付記）
- 8/3リモート（2h）の内容が未反映。録音があれば同様に取り込む
- 8/21訪問までの宿題: オフィス導入用の音源選定＋据置スピーカー候補の提示

## 2026-08-02（ヘルシートラック新プロジェクト要件定義）

### 実施内容
- 圭一郎さんとの打ち合わせ音声（`ジョイファウンデーショントラック.m4a`、7分49秒）を whisper-cpp（large-v3-turbo）でローカル文字起こし（SRT/TXT生成）
- NotebookLM ノートブック「The Joy Foundation Healthy Truck Acoustic System Project」の内容と突き合わせ
- クライアント社名を Web で裏取り: スジャータめいらくグループの「めいらく波動医科学研究所」（1994年設立）。音声中の「百獣会」は「百寿会」の誤認識と判明
- 要件定義書 v1 を作成: `docs/healthy_truck_requirements_v1.md`

### 成果
- 新プロジェクト「乗れば乗るほど健康になるトラック」の要件を文書化
  - 2トントラック数百台規模、時間帯別自然音の自動再生、走行中操作なし
  - 短期=既存車両で実証実験 → 長期=トヨタ等と車両設計段階から連携
  - 康二郎さんへの依頼はシステム構成＋ハード面（スマホ vs 専用スピーカー）の提案

- システム構成・ハード面の提案書ドラフト v1 を作成: `docs/healthy_truck_system_proposal_v1.md`
  - 推奨: ハイブリッド案（実証=スマホ＋車載BTスピーカー → 量産=専用機器/OEM組込み）
  - 体感音響機器 Harmonic Massage の座席組み合わせを差別化要素として提案
  - 実証実験の設計案（5〜10台・4〜8週・ベースライン計測）を逆提案として記載

### 課題・備考
- 「会長」が誰を指すか要確認（スジャータ開発者の日比孝吉会長は2017年逝去）
- スマホ再生か専用機器かは未決定。実証実験の規模・時期・評価指標も未定
- 実装着手前に既存OSS調査＋Codex壁打ちを行う（設計プロセスルール）

## 2026-07-31（3者壁打ち／反応データ実測／画像索引）

### 実施内容

**1. 3者壁打ち（Claude Opus 5 / Claude Fable 5 / ChatGPT）を2ラウンド実施**

1回目のブリーフに事実誤認が4件あり、訂正版で再実施した。
- 誤: 承認ゲートが4ヶ月半閉じている → **正: 既存投稿運用は稼働していた**（X 54件〜6/15、IG 37件〜7/15）
- 誤: カード承認が放置されている → 正: カード方式は3日前に作ったもの
- 誤: セミナー転換が主目的 → **正: 認知獲得が第一。商業100%ではない**
- 追加: 投稿の反応データが取得可能（Tweet ID 53件・IGメディアID 44件が保存済み）

統合案を `docs/agent_team_design_v1.md` に保存。

**2. X の反応データを実測・バックフィル（期限のある作業）**

`collect_metrics.py` を新規作成し、53件を `反応データ` タブ（非表示）へ記録。

**3. 画像索引システムを新規作成**

`index_images.py`。Drive の画像を Vision で索引化し Image カード（IM-）を生成。

### 成果

**反応データの実測（最重要）**

```
X投稿53件: インプレッション中央値 36 / 平均 84 / 最大 1,334
           いいね合計 34 / 反応ゼロの投稿 30/53件（57%）
```

上位5件は**すべてイベント告知**。研究紹介は1本もない。
共通点は「日時が明確・締切がある・固有名詞が強い」。

型別（事後の粗い分類のため参考値）:

| 型 | 件数 | imp中央値 |
|---|---:|---:|
| イベント告知（締切あり） | 13 | 49 |
| 実績・活動紹介 | 7 | 42 |
| その他（知識・思想） | 22 | 31 |
| 問いかけ・見出し型 | 11 | 19 |

**現在の週次ループは、最も到達している型（イベント告知）を作れない**
（イベントタブの日付が4月のもので期限切れ、収集0件）。

**画像の実態**

| | 枚数 |
|---|---:|
| Drive にある画像（圭一郎さん共有分を含む） | **400枚超** |
| ローカルの画像 | 216枚 |
| **実際に投稿で使われたユニーク画像** | **29枚** |
| 投稿の使い回し率 | **44%**（1枚は6回使用） |

画像が足りないのではなく、**「何が写っているか」の索引がないので選べない**状態だった。
原本394ファイルに対して起きていたのと同じ構造。

**画像カード35枚を作成**（`knowledge/images/IM-0001〜0035`）

- 済自然景色 24枚 + 喜田著各本の表紙 11枚
- 使用可否: 可30枚 / 要確認5枚。SNS適性: 高26枚
- 安全装置が機能: 人物の写り込み4枚、他社商標（クルーズ船名 EPIC/NORWEGIAN）1枚を自動隔離
- 出版物11冊の書影を索引化。宝島社・マキノ出版からの刊行が判明

### 3者が一致した結論

- **エビデンスは「コンテンツ源」ではなく「ガードレール」**。EVカードは「書いてはいけないことの辞書」
- ポートフォリオ: 生活場面30-40% / 思想25-30% / **イベント告知20%（実測で追加）** / 活動15% / **研究10%**
- 企画エージェントを新設し、**全カードを毎回渡すのをやめる**（切り口収束の根本原因）
- 重複回避は言い換えではなく**企画レベルで棄却**
- **反応データで自動学習させない**。INSIGHT カード方式（人が承認した仮説として記録）
- 機械検証をLLM化しない。討論型エージェントを作らない
- カード全承認は不要。**AC カード（Approved claim）を投稿OKから機械的に育てる**
- 成長軸の順位: **①供給（カード化）②正確性（修正還元）③読まれ方（反応）**

### 課題・備考

- **Instagram のインサイトが取得できない**。Meta アプリに `instagram_manage_insights` 権限がない
  （HTTP 400 #10）。開発者ダッシュボードでの対応が必要
- メモリのDriveフォルダID `1TbaQla9BUWR...` は**古く404**。圭一郎さん共有の
  `HSC_SNS用画像フォルダ` が本命（400枚超、今まで一度も使われていない）
- **企業案件報告書に実名がある**（本田技研工業・タカラトミー・東急ホテルズ・五島中央病院）。
  納品物であり公表前提の資料ではない可能性が高く、**公表可否の確認が必須**
- 画像カードはできたが**まだ記事に使えない**。週次ループ側に画像選択の仕組みが未実装
- 3者の設計案には**画像の話が一切なかった**。Instagram は画像が主なので大きな欠落
- 重複回避（過去の切り口をプロンプトに渡す）を実装したが、ChatGPT から
  「言い換えレベルの対処。企画レベルで棄却すべき」と指摘済み。暫定策

## 2026-07-29（深夜・launchd 登録と実行環境の問題）

### 実施内容
康二郎さんの承認を得て launchd に登録。**手動起動して検証したところ問題が3件出たため、すべて修正。**

- `com.joyfoundation.weekly-loop.plist` を `~/Library/LaunchAgents/` へ登録（毎日9:00）
- `sync_loop_runtime.sh` 新規作成（実行用コピーへの同期）
- CTA の外部情報申告漏れを修正

### 発見した問題と対処

**1. macOS TCC でプロジェクトが読めない（致命的）**
```
can't open file '.../joyfoundation_project/run_weekly_loop.py': [Errno 1] Operation not permitted
```
launchd から起動されたプロセスは `~/Desktop` 配下にアクセスできない。
既存の自動投稿が `~/sns-poster-runtime/` で動いていたのはこの制約の回避だったと判明。
→ 同じ方式で `~/joyfoundation-loop-runtime/` に実行用コピーを置き、plist をそちらに向けた。

**2. 実行用コピーの同期忘れリスク（新規に発生した運用リスク）**
コピーを持つ以上、カードを承認しても同期しなければ反映されない。
→ `sync_loop_runtime.sh` で一括同期。加えて同期が3日以上前ならループ実行時に警告を出す。
   `sync_approvals.py --apply` の後は必ず同期が必要。

**3. codex が実行用ディレクトリで起動を拒否**
```
Not inside a trusted directory and --skip-git-repo-check was not specified.
```
実行用コピーは git リポジトリではないため。→ `--skip-git-repo-check` を付与。
なお **エラーハンドリングは正しく働き、レビューをスキップして初稿で完走した**（クラッシュしなかった）。

### 成果
- **CTA の外部情報申告漏れが解消**。修正前は3本とも「外部情報なし」だったが、
  修正後は「季節描写は根拠カードにない一般的な状況説明」「団体が研究資料を持ち紹介している
  という活動に関する記述」等を正しく申告するようになった
- launchd 環境で `claude` / Google認証 / シート書き込みが動作することを確認

### 課題・備考
- 明日9:00の初回自動実行を待たずに問題を潰せた。**常駐設定は登録後に必ず手動起動で検証すべき**
- 本番移行時は plist の `StartCalendarInterval` に `Weekday` を足して週1にし、`--test-cards` を外す

## 2026-07-29（夜・ChatGPTレビュー工程の追加）

### 実施内容
康二郎さんのループ検証レビュー3点に対応。

- **`knowledge/glossary.md` 新規**: 用語10語の平易な説明。各語に「禁止する言い方」を併記
- **`RULE-0006`**: 研究の限界は独立見出しを立てて強調しない（限界で記事を終わらせない）
- **`RULE-0007`**: 専門用語には平易な説明を添える。ただし効果の断言に滑らせない
- **ループに②-b/②-c を追加**: ChatGPT（Codex CLI 経由）による読み手視点レビュー → Claude による改稿
  - レビュアーには事実追加の権限を与えない（新しい数値・研究結果の提案は禁止）
  - 改稿側にも「制約に反する提案は採用しない」と明示

### 成果
- ループ全体が **7分**に短縮（生成188秒 + レビュー50秒 + 改稿174秒）。
  プロンプト圧縮の効果が大きく、生成単体では 671秒 → 188秒
- 改稿後、**全3本が機械検証を通過**。note の分級も C → B に改善
- ChatGPT の指摘が改稿に反映されていることを追跡確認:
  - 「【保存推奨】」→「耳で聴く音と、体で感じる音の違い」
  - 「涼しさを取るか、体の調子を取るか」→「冷房との付き合い方に迷いやすい季節かもしれません」
  - 「前後で低い値になった」→「聴く前より聴いた後の値が低かった」
- 専門用語が用語集どおりに置き換わった:
  「有意差」→「偶然とは考えにくい差」／「対照群」→「比較のためのグループ」／
  「HF・LF」→「自律神経の働きを見るための指標」／「STAI」→「不安の程度を点数で測る質問紙」

### ChatGPTレビューの価値（実データ）
機械検証では捕まえられない問題を検出した:
- 「限界や否定材料の比重が大きく、研究結果を慎重に退ける記事として読まれやすい」
  （康二郎さんの指摘と独立に同じ結論）
- 「研究で扱われているのは前後の変化であり**睡眠への効果ではない**ため、
  『寝苦しい夜』から研究結果へ直結して見えないつなぎ方にすること」
  ← 測定していない効果を暗示する構造。数値も NG表現も含まないため機械では検出不能

### 課題・備考
- **懸念していた「自然音と体感音響の区別が薄まる」は杞憂だった。**
  改稿後はむしろ記事全体が「聴く／感じる」の対比で構成され区別が強化された
- **未解決: CTA の主張が `外部情報` として申告されていない。**
  note 末尾「それぞれ触れていただける機会をご用意しています」、
  Instagram「くわしくはプロフィールのリンクへ」は根拠カードにない主張だが、
  モデルの自己申告では `外部情報: なし` になっている。
  数値でもNG表現でもないため機械検証でも捕まらない。申告要件の明文化が必要
- イベント0件のため CTA が一般論に流れている。最新イベント情報が入れば解消する見込み

## 2026-07-29（夕方・週次ループ実装と検証）

### 実施内容
- **`run_weekly_loop.py` 実装**: ①収集 → ②企画・執筆（`claude -p` ヘッドレス）→ ③検証 → ④シート投入
  - 生成に外部APIキー不要（Claude Code の認証を使う）
  - 承認済みカードが0枚なら生成せず停止
- **`knowledge/editorial/RULE-0001〜0005` 作成**（空だった表現ルール層）
- **`com.joyfoundation.weekly-loop.plist`** 作成。検証期間中は毎日9:00想定（**未インストール**）
- 2回実行して端から端まで動作を確認

### 成果
- ループ完走。`週次_レビュー` に3行（X / Instagram / note）が `AI下書き` で投入された
- **検証工程が実際に不良を検出**。1回目で Instagram に NG表現「効果が確認され」が混入していた。
  プロンプトで明示的に禁止していたにもかかわらず生成されており、
  「執筆と検証を別工程にせよ」という Codex の指摘が実データで裏付けられた
- 文字数超過も検出・修正（X 141→108字、Instagram 641→454字、note 2013→1675字）

### 投稿されないことの保証（三重／実物で確認済み）
1. 書き込み先は `週次_レビュー`。稼働中の `~/sns-poster-runtime/` が読むのは `X投稿キュー` / `IG投稿キュー` のみ
2. 書き込むステータスは `AI下書き` / `要確認あり`。投稿トリガーは `投稿予約` のみ
3. `run_weekly_loop.py` は X/Instagram の API を import すらしていない

### 課題・備考
- **検証ツールの誤検知を2件修正**（どちらも真の違反は検出したまま。逆テストで確認済み）
  - `80.9` を「根拠にない数値」と誤検知。空白除去で `Stim.1` + `80.9` → `Stim.180.9` となり境界判定が壊れていた。
    部分一致をやめ、**数値トークンの集合**で照合する方式に変更
  - 「効果が実証」を NG表現と誤検知。実際は「『効果が実証された』と**書けるような話ではない**」という
    模範的な否定文だった。直後30字の否定形を見て除外するようにした
- **生成に約11分（671秒）かかる。** note記事の出力量が主因。毎日回す分には許容だが、
  本数を増やす場合は媒体ごとの並列化が必要
- 生成物が `--no-write` 時に消えていたため、プロンプトと生成結果を必ず `logs/` に保存するよう修正
- プロンプトからカード原文全文を外し、`findings` と `generalization_ng` に絞って約10,000字に圧縮
  （原文は検証工程でのみ使う）
- **イベント0件**。イベントタブの日付が4月のもので7月以降の情報がない。
  日時連動の記事には圭一郎さんからの最新イベント情報が必要
- `週次_レビュー` の3行はテストデータ。本番開始前に削除すること

## 2026-07-29

### 実施内容
承認フローの動作確認（康二郎さんによるテスト承認）。**本番の校正ではないため、テスト後にカードを復元済み。**

- `週次_カード承認` タブに承認欄（解釈の承認／公開の承認／コメント／承認者／承認日）を追加
  - 当初カード承認の置き場所を作っておらず、Markdown 直接編集しかできない状態だった
- `sync_approvals.py` を新規作成。シートの承認結果を Evidence カードへ反映（既定はドライラン、`--apply` で書き込み）
- テストで**設計欠陥が2件露呈したため修正**

### 成果
- 承認 → `approval` 更新 → 両方承認で `status: active` への昇格が正常動作
- `disputed` カード（EV-0002）が正しくスキップされることを確認
- テスト後、カードをバックアップから復元し、シートの承認欄もクリアして本番待機状態に戻した

### 課題・備考
- **欠陥1（修正済み）**: 原本と矛盾する修正指示が素通りしていた。
  Evidence カードの `verbatim` は原本と機械照合済みなので、原本と異なる修正指示は必ず食い違い。
  `detect_conflict()` を実装し2規則で検出:
  - 規則A: 原本に存在しない数値（EV-0011 の `88.8db` を検出。原本は `58.8db`）
  - 規則B: verbatim の書き換え提案（EV-0003 の `9例`→`8例` を検出。1桁差は規則Aでは捕まらない）
  検出時はカードを書き換えず `disputed` にし、`escalation.md` に ESC を自動起票する
- **欠陥2（修正済み）**: シートの原文表示を14行で打ち切っていたため
  「原文が切れていて確認不可」となりレビューが止まった（EV-0005 / EV-0007 で発生）。全文表示に変更
- 数値照合の落とし穴: 空白除去で隣接数値が連結し偽陽性が出る（`図8` + `8.8` → `88.8`）。
  前後が数字でないことを確認する境界チェックを入れた
- **本番の校正は 1 からやり直す**（今回の入力はテストのため無効）

## 2026-07-28

### 実施内容
週次記事の自動生成＋ヒューマンインループ体制の Phase 1（知識層の基盤）を構築。

- **Codex 壁打ち**で設計案を批判レビュー。5つの判断が覆った（詳細は課題欄）
- **`knowledge/` 知識層を新設**（4層構造: Evidence / Approved claim / Editorial rule / Campaign decision）
  - `taxonomy.md`: 圭一郎さんの過去修正の実データから修正種別13コードと出典権威レベル(L0〜L4)を帰納
  - `schema.md`: 研究デザイン（対象/介入/比較/指標/期間/因果性/一般化範囲）を分離したカードスキーマ
  - `verify_cards.py`: 数値捏造・有意差なし項目の欠落・一般化範囲未記入を検出する機械検証
- **Evidence カード12枚を作成**（EV-0001〜0012）。4枚は手作業、8枚は Codex に委譲後レビュー
  - 原本398ファイルのうち「学術論文 学会発表」21件＋「自然音 体感音響 解説」の主要PDFを `pdftotext` で抽出
- **Google スプレッドシートにレビュー用タブ4つを追加**（`create_review_sheet.py`）
  - 週次_レビュー / 週次_内訳 / 週次_カード一覧 / 週次_設定
  - 圭一郎さんが編集するのは5列のみ。修正種別・今後の扱いはプルダウンで選択式

### 成果
- Evidence カード 12枚（転記承認 12/12、解釈・公開承認 0/12）
- `verify_cards.py` 全カード合格
- 原本照合により**過去のSNS投稿の事実誤りの構造を特定**:
  - 西條一止氏の所属は年で変わる（2013年=宝塚医療大学 / 2014年・2018年=筑波技術大学）。
    共著者所属に「筑波大学」も併記されており取り違えやすい
  - 2018年筑波技術大学論文の原文は「LF，HF，LF／HF は自然音群及び対照群に変化がなかった」。
    副交感神経指標に変化はなく、STAI（不安尺度）も自然音群では変化なし（対照群のみ低下）
  - 2013年の体感音響研究では刺激中の反応が10例中6例が交感神経主体、4例が副交感神経主体で一様でない

### 課題・備考
- **ESC-001 未解決（最優先）**: 圭一郎さんの過去修正と原本が食い違う。
  東大抄録の原文は「福祉ワーカー13名・自然音15分・週2回・12週間」だが、
  修正指示は「体感音響20分・2週間・筑波技術大学」。別研究の取り違えか記憶違いか要確認。
  EV-0002 は `disputed` として使用禁止中
- Codex 壁打ちで覆った判断:
  1. 精度劣化の真因は「数字の要約」ではなく**文脈の欠落**
  2. `[要確認]` タグでは負荷は下がらない（自信満々の誤読にタグは付かない）→ A/B/C分級方式へ
  3. RAG不採用は飛躍。検索方式と採用可否を分離したハイブリッドが正解
  4. 記事の編集差分からカードを自動更新してはいけない → 修正理由を選択式で取り承認を経る
  5. パイロット50枚は過大 → 10〜15枚で end-to-end 一周
- 画像PDF3件（2000年健康科学学会 / 2001年横浜市民病院 / 2008年循環器心身医学会）はテキスト抽出不可。OCR必要
- サービスアカウントは Drive 容量を持たず新規スプレッドシートを作成できないため、既存シートにタブ追加した
- homebrew python3.14 は pyexpat が壊れており gspread が動かない。`/usr/bin/python3` を使用

## 2026-06-23

### 実施内容
- 未コミット作業の整理（Work A コミット / 死蔵 Celery scaffold 削除）を PR #30 でマージ
- 康二郎さん本番初使用フィードバック4件のうち、即効性の高い2件を実装:
  1. **画像ドラッグ&ドロップアップロード**（`apps/web/src/app/create/page.tsx`）:
     - 画像リスト領域を drop ゾーン化。ドラッグ中はアウトライン+空状態テキストでハイライト
     - drop された画像ファイル（JPEG/PNG/WebP）のみ抽出し既存 `handleMediaUpload` で R2 アップロード
     - dragenter/leave の深さカウントで子要素跨ぎのちらつきを防止、非画像 drop はエラー表示
  2. **ヘルプ吹き出しの画面端見切れ修正**（`apps/web/src/components/HelpMark.tsx`）:
     - 依存追加なしで、アンカー位置とポップオーバー実寸からビューポート端を検知
     - 水平オフセット補正 + 下端で見切れる場合は上方向にフリップ、resize/scroll で再計算

### 成果
- web typecheck 通過。実ユーザー要望の UX 改善2件を MVP に追加

### 課題・備考
- 残2件（Googleドライブ連携 / RAG ナレッジ積み上げ）は設計・外部API設定を要する大物として別途
- D&D とツールチップ位置は実機でのインタラクション確認が望ましい

### 追加実装（同日）: Google Drive 画像ピッカー（要望②）
- **方式決定**: サービスアカウント方式（既存 Sheets 用 SA を再利用）＋ 選択画像は R2 にコピー（publisher が http URL 前提のため整合）。Picker/個別OAuth は使わずシニア配慮でログイン不要に
- **バックエンド**:
  - `app/services/drive.py`: SA で共有フォルダの画像/サブフォルダ一覧・DL・サムネ取得（thumbnailLink 優先でグリッド高速化）。重い google-api-python-client は使わず google-auth + Drive REST
  - `app/api/drive.py`（`/api/media/drive/*`）: `GET /list`・`GET /thumbnail/{id}`・`POST /import`（DL→既存 upload_original→public_url 返却）
  - config に `GOOGLE_SERVICE_ACCOUNT_JSON/_FILE`・`DRIVE_SHARED_FOLDER_ID` 追加。依存 `google-auth` 追加
  - テスト: 単体7＋API7（Drive はフェイク、R2 は moto）= 全通過
- **フロント**:
  - `components/DriveImagePicker.tsx`: フォルダ階層ナビ＋画像グリッドのモーダル。サムネは認証付き fetch→blob で表示、選択→import→media 配列へ append
  - api-client に `listDriveImages`/`importDriveImage`/`fetchDriveThumbnailBlob`、生成 SDK 再生成
  - create ページに「Drive から選ぶ」ボタン追加
- **検証**: web typecheck / backend pytest（97 passed）/ ruff 通過
- **実 Drive スモークテスト**: 既存 SA で実機検証。Drive API は既に有効、`HSC_SNS用画像フォルダ`(`1vPODCZ9...`)が SA に共有済みと判明（旧 ID `1TbaQla9...` は未共有）。list/download/thumbnail すべて実 HTTP で成功
- **残ops**: 本番のみ Cloud Run に SA資格情報 Secret＋`DRIVE_SHARED_FOLDER_ID=1vPODCZ9...`（gcloud 環境が必要）

### 本番デプロイ（フロント, 同日）
- 第1ゴール=「圭一郎さんが使える状態」を確認（速度優先・急造可だが変更容易性は維持）。投稿公開は当面レビュー/手動ゲート（=方式B）、将来の完全自動投稿(A)はその延長線
- デプロイ機構を確認: フロントは **Vercel CLI 手動**（GH Actions deploy は無効）。本番は #29(ef094be) で止まっていた
- ローカルが Node 25 で `next dev` がハングするが、**Vercel リモートビルド(Node 20)** でプレビュー→本番昇格。#30(実画像プレビュー)・#31(D&D/ヘルプ)・#32(Drive UI) を本番反映
- ブラウザで本番描画＋HelpMark ツールチップ表示を確認。Drive ボタンはバックエンド(Cloud Run)未更新のため一時休眠

---

## 2026-04-23

### 実施内容
- **4/22 自動投稿稼働実績の確認**:
  - 12:00 配信の3件すべて成功（Gmail通知で確認）
    - X「仙台スターライト あと3日」
    - X「カンガルーカップ 協賛告知」
    - IG「日本人だけ？虫の声を聴く感性」
- **圭一郎さんからの 4/21 返信対応**:
  1. **カンガルーカップ日付修正（4/28-30 → 4/28-5/3）**:
     - 全シートを点検し、投稿テキストはほぼ全て既に `4/28-5/3 決勝5/3` で正しい状態と判明
     - 唯一 Xイベント投稿 Row 15「4月まとめ」マスタの `4/27-5/3` を `4/28-5/3` に修正（告知対象外だが整合性確保）
  2. **ファシリテーター研修 第89期（6/12-14）告知の複数回スケジュール**:
     - X 4本 + IG 3本を投稿キューに投入
     - 5/1(金) GW初回告知 / 5/15(木) 1ヶ月前 / 5/29(金) 2週間前 / 6/9(火) 直前リマインド（X のみ）
     - 各回でアングル変更（GW検討 → 残期間カウントダウン → 直前案内）
     - NG表現（効果断言等）回避、画像はマスタの研修会写真を流用

### 成果
- 自動投稿システムが本番安定稼働中（4/22 12:00 配信3/3件成功）
- 圭一郎さん依頼2件完了、6/12開催の認定研修への早期申込導線を確保

### 課題・備考
- 6月投稿分の写真について圭一郎さんが一部差し替え予定（連絡待ち）
- 89期 X #4（6/9 直前）の文面は実際の残席状況確認後、必要に応じて更新可能性あり

---

## 2026-04-22

### 実施内容
- 圭一郎さん向けサポート方針検討（ゼンさんproject側で相談 → joyfoundation に反映）
- ゼンさんPDF「エージェントワークの運用構成と役割分担」を確認し、git ベース非同期エージェント連携の構成を把握
- 圭一郎さん（高齢・PC操作困難）向けサポートアーキテクチャを検討し、以下を決定:
  - **SNS投稿支援**: 既存Webアプリに音声入力AIを統合する方向（音声レイヤ追加のみで完結、PCエージェント常駐は避ける）
  - **PC遠隔エージェント層**: 保留。Webアプリ完成後に再検討
- `APP_DESIGN_SPEC.md` に **Section 14「音声入力AI増分設計 v0.1」** を追加:
  - F-28〜F-32（マイクボタン / リアルタイム音声ブレスト / 対話指示 / TTS確認 / 固有名詞辞書）
  - 技術選定: Whisper API を暫定採用（未決定事項の暫定解消）、`packages/voice-provider/` でプロバイダ抽象化
  - 新規API: `/api/voice/transcribe`, `/api/voice/brainstorm`, `/api/voice/refine`, `/api/voice/vocabulary`, `/api/voice/sessions`
  - 新規モデル: VoiceVocabulary, VoiceSession（90日自動削除）
  - UI設計: シンプルモードに画面下部固定マイクボタン、音声ブレストモーダル、TTS送信前確認モーダル
  - Phase 1.5 組み込み方針、+2〜3週の実装見積もり、VOICE-001〜007 の Issue 案
- 既存設計との整合を確認:
  - F-16（バッチ型音声→投稿）とは実装基盤を共有
  - 決定#6（AI API 両対応）、決定#11-12（org_id RLS）、決定#15（NG 3層チェック）、決定#26-27（シニア配慮ヘルプ）と整合
  - 未決定「音声文字起こし Whisper vs Google STT」を暫定決定としてクロスリファレンス追記

### 成果
- 音声入力機能の増分設計書（Section 14）完成、MVP から Phase 1.5 で組み込む計画に
- 別プロジェクト化の判断回避（feature branch 戦略で Turborepo モノレポの恩恵を維持）

### 課題・備考
- **圭一郎さんの音声サンプルでの Whisper 精度実測**がブロッカー。`scripts/voice-poc/whisper_precision_test.py` を次タスクとして作成予定
- iOS Safari のマイク権限 UX は実機検証が必要
- TTSエンジン（ブラウザ SpeechSynthesis vs OpenAI TTS）の選定は未決
- 本設計は `main` ブランチ上の追記（計画ドキュメントのため）。実装着手時に `feat/voice-input` を切る

---

## 2026-04-22（夜・GCP + Vercel 本番稼働）

### 実施内容
- **GCP Cloud Run セットアップ**（手順書どおりに実行、所要 約60分）:
  - プロジェクト `shc-sns-calendar`（番号 817894013861）作成＋Billing 紐付け
  - API 有効化: run / artifactregistry / secretmanager / iamcredentials / cloudbuild
  - Artifact Registry `sns-calendar-api`（asia-northeast1）
  - Secret Manager に 9 シークレット登録（Supabase / X / Meta / R2 / INTERNAL_API_TOKEN）
  - Service Account 2種（cloud-run-runtime / github-deployer）
  - Workload Identity Federation（github-pool + github-provider）
  - GitHub Secrets 登録（GCP_*、INTERNAL_API_TOKEN、CLOUD_RUN_API_URL）
  - GitHub Variables 設定（CLOUD_RUN_ENABLED / PUBLISH_FLUSH_ENABLED = true）
- **Cloud Run 初回デプロイ**:
  - 1回目: config.py の `parents[3]` が IndexError で起動失敗
  - fix PR #27 で `_safe_env_file` ヘルパー追加、try/except で None 許容化
  - 2回目: デプロイ成功 → `/health` 200、`/internal/publish/flush` 401/200 確認
- **GH Actions Cron 疎通**: `publish_flush.yml` 手動トリガー → 6秒で success
- **Vercel デプロイ**:
  - Vercel CLI ログイン（GitHub OAuth）
  - プロジェクト `shc-sns-calendar-web` 作成
  - 初回デプロイ失敗（Next.js 未検出） → Vercel API で rootDirectory を `apps/web` に変更
  - 2回目デプロイ成功: https://shc-sns-calendar-web.vercel.app
- **Cloud Run CORS 連動**:
  - `FRONTEND_URL` 環境変数を Vercel URL で更新 → Cloud Run 新リビジョン `sns-calendar-api-00003-dfd`
  - OPTIONS preflight で `access-control-allow-origin: https://shc-sns-calendar-web.vercel.app` を確認

### 成果
- **完全無料スタック**が本番稼働開始（Supabase + Vercel + Cloud Run + R2 全て無料枠内）
- フロント〜バックエンド〜DB〜Realtime〜Cron の5層が疎通
- **固定費 $0/月**で SaaS 販売可能な基盤が完成
- 圭一郎さんがアクセスできる本番URL確定: https://shc-sns-calendar-web.vercel.app

### 残課題
- Supabase Auth Settings → Site URL / Redirect URLs に Vercel URL を登録（ブラウザから認証メールのリダイレクトを成立させるため）
- 圭一郎さんユーザー登録 + SNS OAuth 連携（X / IG Business）
- ARCH-005 Resend（認証メール用 SMTP、現状 Supabase デフォルト SMTP 使用中 = 1日3通制限）
- B2 ファシリ89期告知反映
- Supabase 運用検討（#12）

### 備考
- Vercel プロジェクト設定（rootDirectory / buildCommand / installCommand）は CLI で直接変更できず、Vercel API (`PATCH /v9/projects/{id}`) で更新
- `vercel.json` を monorepo root に置くアプローチは Next.js 検出に失敗、project-level 設定のほうが安定
- Cloud Run の環境変数更新は `gcloud run services update --update-env-vars=` で新リビジョン作成（イメージ再ビルド不要）

---

## 2026-04-22（夕方・D案実装着手：ARCH-001/002/003/004 コード側完了）

### 実施内容
- **ARCH-003 Realtime 移行**:
  - Supabase migration `20260422120000_enable_realtime_notifications.sql` 追加・本番適用
  - `apps/api/app/api/notifications_ws.py` 削除、`main.py` から /ws ルート削除
  - `notifier.py` の `_publish_redis` + redis/json/os 依存削除
  - Web 側に `@supabase/supabase-js` 追加、`apps/web/src/lib/supabase.ts` 新規、`useNotifications.ts` を Realtime 版に書き換え
  - `apps/web/.env.example` に `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` 追加
- **ARCH-001 pg_cron + publish_queue**:
  - Supabase migration `20260422130000_publish_queue_pgcron.sql` 追加（マイグレーションファイルはコミットのみ、本番適用は別途）
  - `apps/api/app/api/internal.py` 新規、`/internal/publish/flush` エンドポイント実装
  - `config.py` に `INTERNAL_API_TOKEN` 設定追加
  - `.github/workflows/publish_flush.yml` 新規（5分毎、`PUBLISH_FLUSH_ENABLED=true` 条件付き）
- **ARCH-002 Celery 撤廃 + Publisher service**:
  - `apps/api/app/services/publish_flush.py` 新規（既存 `scheduled_posts.py` のロジック移植）
  - `apps/api/app/tasks/` ディレクトリ一式削除（celery_app.py / scheduled_posts.py / __init__.py）
  - `tests/tasks/test_scheduled_posts.py` / `tests/test_celery.py` 削除
  - `railway.worker.json` / `railway.beat.json` / `railway.json` 削除
  - `pyproject.toml` から `celery` / `redis` 依存削除（poetry lock 再生成）
  - `apps/api/tests/api/test_internal.py` 新規（token 認証テスト 5件）
- **ARCH-004 Cloud Run デプロイ準備（コード側のみ）**:
  - `.github/workflows/deploy-backend.yml` を Cloud Run 用に書き換え（Workload Identity Federation）
  - `railway.json` 削除
  - 既存 Dockerfile はそのまま利用可（PORT 環境変数対応済み）
  - `/health` エンドポイントも既存（HealthResponse 含む）

### 成果
- **Celery + Redis 依存完全撤廃**。Docker イメージの軽量化（redis/celery/amqp/billiard 等 13パッケージ削除）
- **通知配信が Supabase Realtime に統合**。RLS の SELECT policy が認可境界として機能、サーバー側の JWT 検証・接続管理が不要
- **予約投稿ジョブ基盤が完成**（pg_cron → publish_queue → FastAPI /flush → publisher/orchestrator）
- **Cloud Run デプロイワークフロー**準備完了（GCP 側のプロジェクト・WIF 設定は次タスク）
- テスト: API 78 passed / Frontend typecheck/lint/build すべて成功
- OpenAPI スキーマ更新（`internal` ルート追加、`tests/api/test_internal.py` で検証）

### 残課題
- **pg_cron マイグレーション本番適用**: 動作確認後に `supabase db push` で `20260422130000` を適用
- **GCP セットアップ**（手動）: プロジェクト作成・API 有効化・Artifact Registry 作成・Workload Identity Federation
- **GitHub Secrets 追加**:
  - `INTERNAL_API_TOKEN`（`openssl rand -hex 32` で生成）
  - `CLOUD_RUN_API_URL`（Cloud Run デプロイ後）
  - `GCP_PROJECT_ID` / `GCP_WORKLOAD_IDENTITY_PROVIDER` / `GCP_SERVICE_ACCOUNT`
- **GitHub Variables**:
  - `CLOUD_RUN_ENABLED=true`（deploy-backend 有効化）
  - `PUBLISH_FLUSH_ENABLED=true`（GH Actions cron 有効化）
- **ARCH-005 Resend**: 未着手

### 備考
- 既存 `.github/workflows/auto_post.yml`（CSV シート連携の自動投稿）は別用途なので触らない
- Phase 1 MVP の実装コード（`apps/api/app/services/publisher/`）は流用。Celery を剥がして同期呼び出しに変更しただけ
- ブランチ: `feat/arch-003-realtime-migration`（PR #25）。当初は ARCH-003 単体だったが、時間効率から ARCH-001/002/004 を同じブランチに積んでいる

---

## 2026-04-22（午後・P1→D案方針転換）

### 実施内容
- **P1. Supabase 本番準備 完了**:
  - 既存プロジェクト `sns-calendar-app`（ref: `msghvqclexpvgkrctxug`, Tokyo, Free tier）にリンク
  - マイグレーション6本を本番適用（`supabase db push`）
  - GitHub Secrets に SUPABASE_URL / ANON_KEY / SERVICE_ROLE_KEY 登録
  - `apps/web/.env.example` を新規作成（Web は API 経由のため NEXT_PUBLIC_API_BASE_URL のみ）
- **方針転換**: 圭一郎さん個人利用 → **SaaS 販売化を目標** に変更。固定費ゼロの設計を優先
- **D案「無料スタック移行計画」決定**:
  - 現行 Phase 1 MVP: Railway ($5〜10/月) + Celery + Redis 前提
  - 移行後: Cloud Run (Scale-to-zero) + pg_cron + GitHub Actions Cron + Supabase Realtime
  - 固定費 **月額 0 円**、販売収益と従量課金で連動スケール
- `APP_DESIGN_SPEC.md` に **Section 15「無料スタック移行計画 v0.1」** を追加:
  - 15.1 背景と目的（SaaS販売前提の固定費ゼロ設計）
  - 15.2 現行 vs D案の構成比較（8レイヤ）
  - 15.5 ARCH-001〜005 実装タスク（計 2〜3 日）
  - 15.7 監視と昇格トリガー（7サービス別の警告閾値）
  - 15.8 リスクと緩和策（コールドスタート / 二重化 / 仕様変更）
- **ARCH-001〜005 Codex ブリーフィング作成**:
  - ARCH-001: Celery Beat → pg_cron + GH Actions Cron
  - ARCH-002: Celery Worker → FastAPI 内部エンドポイント
  - ARCH-003: Redis PubSub → Supabase Realtime
  - ARCH-004: Railway → Cloud Run（Workload Identity Federation）
  - ARCH-005: Resend 導入（認証メール・投稿結果通知）

### 成果
- 販売化可能な **固定費ゼロ** アーキテクチャの設計書完成
- 5つの Codex ブリーフィングで実装着手準備完了（工数見積もり 2〜3 日）
- Phase 1 MVP を破棄せず、漸進的に置換する移行戦略（`feat/free-stack-migration` ブランチ）

### 課題・備考
- **Vercel Hobby Free の商用利用規約**確認必要（SaaS 販売で規約違反にならないか）
- **Cloud Run Workload Identity Federation** の初回セットアップ（GCP プロジェクト・IAM・OIDC）
- **独自ドメイン取得**（Resend SPF/DKIM、Cloud Run カスタムドメイン）未決
- **販売モデル**（Freemium / Per-seat / Per-org）は BIZ-001 別設計書で扱う
- 本日は設計フェーズ完了、実装は明日以降。今日は P2 Vercel も着手せず（Cloud Run 先行が合理的）

---

## 2026-04-16（午後）

### 実施内容
- Codex壁打ち R5: Phase 1 実装計画（実装寄り3テーマ）
- 実装計画書作成（`design/design/IMPLEMENTATION_PLAN.md`）:
  - Turborepo + pnpmモノレポ構成（確定版ディレクトリ構造）
  - OpenAPI自動生成パイプライン（FastAPI Pydantic → TypeScript型）
  - インフラ/DevOps設計（Vercel + Railway + Supabase + R2）
  - FullCalendar + dnd-kit統合設計（Phase 1はFC公式Draggableのみに決定）
  - 30 Issue / 4 Sprint / 7-8週間のIssue分割
  - コスト試算（MVP: ~$5-15/月、PMF後: ~$60-80/月）
- Postiz（OSS SNSスケジューラ）のアーキテクチャを参考調査
- APP_DESIGN_SPEC.md に決定事項#20-25を追記
- UIモックアップに下書き一覧ページを追加（全5画面に）

### 成果
- 設計フェーズ完了 → 実装着手可能な状態に
- 設計ドキュメント合計8ファイル完成

### 課題・備考
- 未読メール（4/15 定期スケジュール）の対応が必要
- WS参加費変更（¥2,500→¥3,000）のシート反映が必要
- 音のウエルビーイングOnline 5/19開始が確定
- `sns_accounts.access_token` の at-rest 暗号化は follow-up issue 化が必要（pgcrypto 等を別Issueで導入）

---

## 2026-04-16

### 実施内容
- Codex壁打ち R3: RLS設計レビュー + LLM品質評価基盤
- RLS設計書作成（`design/design/RLS_DESIGN.md`）:
  - 全テーブルのRLSポリシー設計（SQL付き）
  - org_id方式のマルチテナント設計（Phase 2チーム機能への拡張準備）
  - トークン保護設計（sns_accounts_safeビュー）
  - service_role vs ユーザーロールの使い分けマトリクス
  - インデックス戦略（カレンダー表示パフォーマンス99%+改善見込み）
  - pgTapテスト例
- LLM品質評価基盤設計書作成（`design/design/LLM_EVAL_DESIGN.md`）:
  - 6軸品質メトリクス設計（トーン/正確性/エンゲージメント/文字数/NG/自然さ）
  - 3層ハイブリッドNGチェック（ルールベース→辞書→LLM）
  - LLM-as-Judge評価プロンプト設計（バイアス対策込み）
  - 薬機法NGワード辞書設計
  - プロンプトバージョニング + eval_logsテーブル設計
  - ABテスト基盤設計（オフライン/オンライン）
  - コスト試算: 1投稿あたり~$0.032、月60件で~$5.52
- APP_DESIGN_SPEC.md に決定事項#11-17を追記
- Codexブリーフィング作成（`docs/codex_rls_llm_briefing.md`）
- Codex壁打ち R4: note.com連携の法務/規約確認
- note.com規約調査（第22版 2026/1/15制定）:
  - 公式投稿APIは存在しない（公開予定も未定）
  - 非公式APIエンドポイントは405 Not Allowedでブロック済み
  - 利用規約でスパム的活動・技術的措置の回避を禁止
  - 競合ツール（Buffer/Hootsuite/Later）もnote未対応
- note連携設計書作成（`design/design/NOTE_INTEGRATION_DESIGN.md`）:
  - Phase 1: 下書き補助+手動投稿（リスクゼロ）
  - RSS連携で投稿済み自動検知（公式サポート）
  - oEmbed活用の記事プレビュー
  - publisher抽象化でAPI公開時に即応可能な設計
  - note社への事前問い合わせテンプレート作成
- APP_DESIGN_SPEC.md に決定事項#18-19を追記

### 成果
- **優先アクション5件中5件すべて完了**
- 設計ドキュメント合計7ファイル:
  - APP_DESIGN_SPEC.md（更新）
  - CODEX_REVIEW_20260416.md
  - PLATFORM_MATRIX.md
  - RELIABILITY_DESIGN.md
  - RLS_DESIGN.md（新規）
  - LLM_EVAL_DESIGN.md（新規）
  - NOTE_INTEGRATION_DESIGN.md（新規）

### 課題・備考
- 評価データセット構築には既存承認済み投稿50件の収集が必要（圭一郎さんとの作業）
- note社への問い合わせを実施推奨（テンプレート準備済み）
- 未決定事項: 評価モデル選定、自動再生成閾値はデータセット構築後に決定

## 2026-04-09

### 実施内容
- イベント投稿シート（X・IG両方）に「画像リンク」「画像表示」列を追加（IMAGE関数で自動サムネイル表示）
- 圭一郎さんメール確認（2通）: IGイベント投稿へのフィードバック + カンガルーカップ2026情報
- IGイベント投稿シート一括修正（46セル更新）:
  - No.1: 第90期→第88期
  - No.4: 4月オンライン講座→延期（5月開始）
  - No.5: 体験WS→満員御礼+5月募集構成に修正
  - No.8: カンガルーカップ→岐阜メモリアルセンター、活動紹介トーンで記事作成
  - No.12,20,25: オンラインWS費用¥4,000→¥3,000に修正、5月初回強調
  - No.13,14: 告知不要に変更
  - No.15: 太陽食品コラボ6月→6/5-6/6の2日間に修正
  - No.16: 第91期→第89期
  - No.21: 抗加齢医学学会→学会発表の告知記事作成
- Xイベント投稿シート修正+追加:
  - Row2 オンライン講座→延期、Row8 第91期→第89期
  - 6件追加: カンガルーカップ、オンラインWS 5-7月、太陽食品6月、抗加齢医学学会
- カンガルーカップ公式HP情報取得（会場: 岐阜メモリアルセンター、選手へのサウンドヒーリングサポート提供）

### 成果
- IGイベント投稿: 25件中11件修正、2件告知不要、12件変更なし
- Xイベント投稿: 既存2件修正 + 6件新規追加（計14件）
- 全記事の確認メモ列に「対応済」ステータスを記載
- メモリ4ファイル保存（フィードバック、カンガルーカップ、オンラインWS正式情報、打ち合わせ予定）

- Xイベント投稿シートの既存記事修正+不足イベント6件追加（計14件に）
- カンガルーカップ添付資料6件をダウンロード・ローカル保存（イベント資料/カンガルーカップ2026/）
  - SNS用DOCX、開催要項PDF、写真4枚
- DOCX・PDFから詳細情報を抽出:
  - 正式日程: 4/27(月)〜5/3(日)（当初4/28-5/2から修正）
  - 会場: 長良川テニスプラザ（ハードコート13面）
  - 賞金総額US$100,000
  - 昭和西川ムアツマット×KITAサウンドヒーリングのセルフケアコーナー設置
  - 選手リカバリーケアとして体感音響・自然音を提供
- IG・X両方のカンガルーカップ記事を正式情報で更新

### 課題・備考
- 自由が丘打ち合わせの日程返信が必要（4/14 or 15）
- カンガルーカップ出場選手発表は4/15頃 → 発表後にSNS投稿内容を更新する可能性あり
- カンガルーカップ資料のDriveアップロード未完了（サービスアカウントにストレージ制限あり。手動アップロードが必要）

## 2026-04-08

### 実施内容
- イベント投稿専用シート作成（「Xイベント投稿」「IGイベント投稿」タブをスプレッドシートに追加）
- Googleカレンダー(keiichiro.kita@gmail.com) 4〜7月の全イベント取得・照合
- 公式サイト(sound-healing.jp)・チラシ・イベント資料と突き合わせて照合レポートPDF作成
- IGイベント投稿記事25件を情報確認ステータス付きで一括作成（✅公式確認済13件/⚠️要確認7件/❓未確認5件）
- 圭一郎さんへ確認依頼メール送信（確認事項6項目）
- X自動投稿にリプライ機能を実装（K列「リプライテキスト」追加、投稿後5秒待機→自動リプライ）
- 即時投稿コマンド `post_now.sh` 追加（GitHub Actionsの遅延を回避）
- Day4投稿実行（X: ここちよい音の日+リプライ / IG: 体感音響カルーセル3枚）
- Cloudflare R2セットアップ完了（サブスクリプション有効化→バケット作成→Public URL有効化→APIトークン発行）
- GitHub Secretsに R2環境変数5件登録（R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL）
- R2接続テスト成功（アップロード→公開URL→削除の全フロー確認）
- IGカルーセルテスト投稿成功（3枚: 1920x1080, 800x1200, 500x500）
- IG投稿のリサイズ処理を無効化（元サイズで投稿に変更）
- 汎用画像リサイズツール `tools/image_resizer.py` として独立化（プリセット10種対応）
- .envにR2環境変数追加

### 成果
- イベント照合レポート: `イベント照合レポート_2026-04-08.pdf`（4ページ、公式ソース付き）
- IGイベント投稿: 25件作成完了、圭一郎さん確認待ち
- リプライ機能: コミット `6fa704b` でpush済み、Day4で動作確認済み
- 即時投稿: コミット `cf9f475` でpush済み
- Cloudflare R2: バケット `shc-sns-temp-images`（APAC）稼働中
- Public URL: `https://pub-b525379228434e46a50c4d3f1edae5c7.r2.dev`
- IG投稿パイプライン: Google Drive画像→R2アップロード→IG API投稿→R2削除の全フロー動作確認済み
- コミット: `ed51ef0`

### 課題・備考
- 圭一郎さんからのイベント確認回答待ち（⚠️要確認7件/❓未確認5件）
- 確認後: IG記事修正 → X記事作成の流れ
- GitHub Actions schedule cronは遅延が大きい（今回13:40予約→14:53実行）。正確な投稿には `./post_now.sh` を使用
- IGグリッド表示では4:5画像が1:1クロップされるため、リサイズは無効化し元サイズ投稿に変更
- resize_for_ig()関数はコード内に残存（将来再利用可能）
- 今後のシステム構築時は既存OSS調査+Codex壁打ちを設計プロセスに組み込む方針を決定

## 2026-03-10（ミーティング方針決定・イベント資料保存）

### ミーティング議事録PDF作成
- NotebookLMの録音トランスクリプト + Gmailの講座名提案を統合
- `generate_meeting_pdf.py` で11ページのPDF生成 → `ミーティング議事録_20260310.pdf`
- 主な決定事項:
  - ターゲット: 30〜50代女性（子育て中〜終えた層）
  - オンライン講座設計: 無料体験→有料コース（月額制）
  - 集客ファネル: Instagram → LINE → Zoom体験 → リアル体験会 → 資格取得
  - YouTube戦略: 自然音BGM長尺動画で再生時間を稼ぐ
  - 講座名候補: 圭一郎さんから複数案提示（「音の健康法」「Harmonic Self Care」等）

### イベント資料保存
- 「ここちよい音の日」チラシPDF 2点をGmailからダウンロード・保存
  - `イベント資料/ここちよい音の日_20260402-04/★チラシ：太陽食品＆SH協会のコラボ企画 『ここちよい音の日』2026.4.2-4.pdf`（4.5MB・表面）
  - `イベント資料/ここちよい音の日_20260402-04/★チラシ裏面　2026.4.2-4.pdf`（842KB・裏面）
- イベント概要:
  - 太陽食品世田谷店 & SH協会コラボ
  - 2026年4月2日(木)・3日(金)・4日(土) 13:00〜16:00
  - 体験500円（オーガニック試飲付）
  - KITAサウンドヒーリング体験（約10分の肩腰ケア）

### オンライン講座告知案（Gmailより保存）
- 圭一郎さんからの転送メール「4月の新オンライン講座スタート」を確認
- 講座名決定: **「音のウェルビーイング」オンライン Harmonic Science 体験講座**
- サブタイトル: 世界の自然音と呼吸で整えるセルフケア
- 日程:
  - 4月14日（火）10:00〜12:00（Zoom・4,000円）
  - 4月23日（木）10:00〜12:00
- 「音の旅シリーズ」4テーマ: 森の音と呼吸 / 海の音と声 / 風の音と瞑想 / 夜の音と深い呼吸
- 保存先: `イベント資料/オンライン講座_202604.md`

### スターライトヒーリング追加公演情報（Gmailより保存）
- 圭一郎さんからのメール「スターライトヒーリングマラマハワイ追加公演決定」を確認
- イベント: **Star Light Healing Malama Hawaii** 追加公演
- 日程: 2026年4月12日（日）13:30〜14:20
- 会場: さいたま市宇宙劇場（JACK大宮3階）
- 料金: 大人620円 / 小人310円
- 後援: ハワイ州観光局
- チラシ画像2点を保存:
  - `イベント資料/スターライトヒーリング_20260412/★さいたま市star_light_healing_2025.jpg`（3.0MB・表面）
  - `イベント資料/スターライトヒーリング_20260412/★star_light_healing_2025_v4_fix_ura.jpg`（2.8MB・裏面）
- イベント情報: `イベント資料/スターライトヒーリング_20260412/イベント情報.md`

---

## 2026-03-09（NotebookLM共有ノートブック確認・SNS方針反映）

### NotebookLM ノートブック調査

#### 確認結果
- 圭一郎さん（keiichiro.kita@gmail.com）から**28件のNotebookLM招待**がGmailに到着
- ソース: ミーティング録音（m4a）、YouTube動画等をNotebookLMにアップロードしたもの
- ✅ **全28件受諾完了**（Gmail招待リンク経由で全件NotebookLMに追加済み）

#### 受諾済みノートブック（全28件）

**カテゴリA: サウンドヒーリング科学・メソッド（7件）**
1. Harmonic Healing: Breathing with Infinite Words — 呼吸法×サウンドクッション×骨伝導
2. Harmonic Healing: Autonomic Resilience through Sound and Vibration — 自律神経×音×振動
3. Sound Healing: Nature, Harmony, and Bone Conduction Methods — 自然音×骨伝導メソッド
4. Resonant Harmony: The Evolution of Sound Healing — サウンドヒーリングの進化
5. Harmony of the Body: Sound, Nature, and Self-Healing — 身体×自然×自己治癒
6. Sound Healing and the Resonance of Nature — 自然の共鳴
7. Resonating Wellness: Sound Therapy and the Cellular Flow of Life — 細胞レベルの音響療法

**カテゴリB: 自然音・地球の音アーカイブ（4件）**
8. The Resonant Soul of Nature — 自然の響き
9. The Healing Power and Global Branding of Japanese Nature Sounds — 日本の自然音ブランディング
10. Earth Sound Archives and the Spirit of Nature — 地球の音アーカイブ
11. Earthly Soundscapes and the Preservation of Natural Heritage — 自然遺産の保存

**カテゴリC: ビジネス・ブランディング・イベント（4件）**
12. Global Networking for Harmonic Healing Workshops — ワークショップネットワーク
13. Global Healing: Planning Interactive Amneck Online Workshops — オンラインワークショップ企画
14. Taiyo Foods and Sound Healing Association Collaborative Event 2026 — 太陽フーズコラボ
15. Sonic Branding and Sleep Environments for Professional Athletes — アスリート睡眠環境

**カテゴリD: 哲学・スピリチュアル・意識（7件）**
16. Awakening the Divine Genetic Blueprint for 2026 — 遺伝子の覚醒
17. The Sound of Self-Love and Inner Resilience — 自己愛と内なる回復力
18. The Sound of Universal Grace: Cultivating the Inner Mother — 宇宙の恩寵
19. Spiritual Independence Through Mindful Association Content — スピリチュアル自立
20. The Creative Power of Language and Resonance — 言葉と共鳴の創造力
21. Eternal Presence and the Dawn of Open Contact — 永遠の存在
22. Awakening the Divine Blueprint for 2026 — 神聖な青写真

**カテゴリE: AI・テクノロジー・アート（3件）**
23. The Harmony Place: Cultivating Human Sensibility in the AI Age — AI時代の人間感性
24. The Vibration of Intelligence: Resonance Beyond AI — AI超越の振動
25. The Vibration of Being: Art, Consciousness, and Cosmic Resonance — 宇宙的共鳴

**カテゴリF〜H（各1件）**
26. The Resonance of Physical Joy and Emotional Peace — ウェルビーイング
27. The Art of Nature and the Nature of Art — イェール大学シンポジウム
28. Guide to the School Public Transmission Compensation System — 法律・制度

#### SNS戦略への反映ポイント
- **高優先**: アスリート×睡眠×自然音（企業案件テーマ）、呼吸法メソッド（実践系コンテンツ）
- **中優先**: AI時代の感性論、自然音グローバルブランディング
- **note向け**: バイブレーション哲学、静寂と真の音、芸術×科学の融合

#### 保存場所
- `NotebookLM_アップロード用/NotebookLM_ノートブック一覧.md` に全28件の一覧・分類・詳細・方針を保存

#### 既存ノートブック（マイノートブック）も確認
- 協会誌シリーズ（2011-2025）: 計107ソース
- 自然音・体感音響 解説①②: 計55ソース
- 学術論文・学会発表: 38ソース
- 体験談・事例集: 8ソース
→ これらと新規ノートブックを組み合わせた深いSNSコンテンツ制作が可能

### 次のアクション
1. ~~残り23件のNotebookLM招待を受諾~~ ✅完了
2. ~~各ノートブックの内容確認・概要追記~~ ✅完了（全28件の概要・SNS活用案を追記済み）
3. 確認内容をInstagram/X/note投稿計画に反映
4. アスリート×睡眠テーマを企業案件カテゴリの新規SNSシリーズとして企画
5. 太陽フーズイベント（2026.4.2-4「ここちよい音の日」）の告知コンテンツを早急に準備
6. X API クレジット購入の判断（圭一郎さんに確認）
7. Instagram/LINE APIセットアップ（圭一郎さんの依頼事項完了待ち）

---

## 2026-03-09（X API セットアップ完了・課金確認）

### X Developer Console セットアップ

#### 完了項目
- Developer登録完了（アカウントID: 2029826061224267778）
- アプリ作成済み: 「2029826061224267778SFH_Science」（App ID: 32523502, Status: ACTIVE）
- ユーザー認証設定: Read+Write権限、ウェブアプリ/ボット、コールバックURI設定済み
- 全認証情報取得済み:
  - Bearer Token
  - Consumer Key (API Key + API Secret)
  - Access Token + Access Token Secret（@SFH_Science用、Read+Write権限）
  - OAuth 2.0 Client ID + Client Secret
- `.env` ファイル作成済み（sns-auto-poster/.env）
- 認証テスト成功: `@SFH_Science`（サウンドヒーリング協会）として認証確認

#### 課題: API クレジット不足
- X API は「Pay Per Use」方式に移行済み
- 現在のクレジット残高: **$0.00**
- ツイート投稿（POST /2/tweets）には**クレジット購入が必要**（402 Payment Required）
- 認証・読み取り（GET）は成功するが、書き込み（POST）は有料
- → クレジット購入（最低$5〜）の判断が必要

### 次のステップ
1. X API クレジット購入の判断（圭一郎さんに確認）
2. 圭一郎さんへの依頼事項実施（下記参照）
3. Instagram API / LINE API セットアップ

---

## 2026-03-06（Instagram API セットアップ調査）

### 調査結果

#### Facebookページ確認
- **ページ名**: サウンドヒーリング協会 The Society for Harmonic Science
- **URL**: https://www.facebook.com/harmonicscience
- **フォロワー**: 601人
- **カテゴリ**: 団体
- ※既存ページあり。管理者は圭一郎さん（推定）

#### Instagramアカウントセンター確認
- @harmonicscience_jp はビジネスアカウント（確認済み）
- Facebookページとは**未接続**
- アカウントセンターにInstagramのみ表示、Facebookアカウント未追加

### 圭一郎さんへの依頼事項（まとめて実施）

以下3点を圭一郎さんに依頼する必要あり：

1. **Facebookページの管理者追加**
   - 「サウンドヒーリング協会」Facebookページ（https://www.facebook.com/harmonicscience）に康二郎さんのFacebookアカウントを管理者として追加
   - 手順: Facebookページ → 設定 → ページの役割 → 管理者を追加

2. **InstagramとFacebookページの接続**
   - @harmonicscience_jp を「サウンドヒーリング協会」Facebookページに紐付け
   - 手順: Instagramアプリ → 設定 → ビジネスツールと管理 → リンク済みのアカウント → Facebook → ページを選択
   - ※圭一郎さんのFacebookアカウントでInstagram管理権限がある場合はそちらから実施

3. **Facebook Developer登録（オプション）**
   - https://developers.facebook.com/ で開発者登録
   - 電話番号認証が必要
   - ※康二郎さんのFacebookアカウントでも可（ページ管理者に追加後）

4. **LINE公式アカウントのログイン情報確認**
   - LINE公式アカウント（@868hqnfw）の管理画面ログインに使ったアカウント情報を共有
   - 管理画面: https://manager.line.biz/
   - Messaging API有効化のためにログインが必要

### 依頼後に康二郎さんが行う作業
- Facebook Developer Appの作成
- Instagram Graph APIの権限追加
- アクセストークン生成
- `.env` ファイルへの設定

---

## 2026-03-02（SNS Auto Poster: Instagram API実装・コンテンツ変換）

### 実施内容

#### 1. 環境構築・ビルド修正
- `date-fns-tz` v2→v3 にアップグレード（date-fns v3との互換性）
- `@line/bot-sdk` v9 の型定義変更に対応
  - 旧 `Message` 型と新 `messagingApi.Message` 型の互換性問題を修正
  - `getNumberOfFollowers` → `getFollowers` APIに移行
- `twitter-api-v2` の `media_ids` タプル型修正
- 未使用import一掃（`isBefore`, `logger` in test scripts）
- `npm run build` ゼロエラー達成

#### 2. Instagram Graph API 実装（Phase 5完了）
- `src/platforms/instagram.ts` フル実装
  - 単一画像投稿: コンテナ作成 → ステータス確認 → 公開の3ステップ
  - カルーセル投稿: アイテムコンテナ → カルーセルコンテナ → 公開
  - キャプション整形（2200文字制限、ハッシュタグ30個制限）
  - 認証確認（`verifyCredentials`）
  - アカウント情報取得（`getAccountInfo`）
- `src/platforms/index.ts` にInstagramハンドラー登録
- `src/scripts/test-instagram.ts` テストスクリプト作成

#### 3. コンテンツ変換スクリプト
- `src/scripts/convert-content.ts` 作成
  - X投稿90本.md → 90件のYAMLファイル
  - Instagram投稿48本.md → 13件のYAMLファイル（キャプション付きのみ）
  - 合計103件のスケジュール済みYAMLファイル生成
  - 2026-03〜05の3ヶ月間にスケジュール配置

#### 4. 動作検証
- `npm run build` — ゼロエラー
- `npx tsx src/scripts/convert-content.ts` — 103ファイル生成成功
- `npm start` — メインフロー正常動作（104投稿読み込み、0件投稿対象）

### 生成ファイル
| ディレクトリ | ファイル数 | 内容 |
|-------------|-----------|------|
| content/posts/2026-03/ | 42 | X + Instagram投稿 |
| content/posts/2026-04/ | 30 | X投稿 |
| content/posts/2026-05/ | 31 | X + Instagram投稿 |

### Phase完了状況
| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 1 | プロジェクト構築 | ✅ 完了 |
| Phase 2 | Twitter API | ✅ 完了 |
| Phase 3 | LINE API | ✅ 完了 |
| Phase 4 | スケジューラー | ✅ 完了 |
| Phase 5 | Instagram API | ✅ 完了 |

### 次のステップ
- [ ] Instagram APIのアクセストークン取得・.env設定
- [ ] 各プラットフォームの認証テスト実行
- [ ] 画像URLの準備（Instagram投稿用に公開URLが必要）
- [ ] GitHub Actionsの定期実行テスト

---

## 2026-02-24（noteアカウント開設・海外展開調査）

### 実施内容
- **noteアカウント開設完了**
  - アカウント名: サウンドヒーリング協会
  - メール認証: 完了
  - 投稿可能状態

### 海外展開調査結果

#### noteの海外対応状況
- 2026年2月〜: 自動多言語対応機能テスト開始予定
- GoogleのAI翻訳で英語など多言語に自動変換
- 現時点では日本国内向けサービスがメイン

#### 海外向け代替プラットフォーム
| プラットフォーム | 特徴 | 用途 |
|-----------------|------|------|
| **Medium** | 海外版note的存在、SEO強い | 英語圏への情報発信 |
| **Substack** | ニュースレター特化 | ファンとの深い関係構築 |

#### Instagram/X/YouTube 海外向け戦略
- **Instagram**: ビジュアル中心で言語の壁を超えやすい。日英併記キャプション推奨
- **YouTube**: タイトル・説明文の翻訳追加、字幕設定が重要
- **X**: 英語ハッシュタグ活用（#soundhealing #naturetherapy #meditation）

#### 推奨戦略（2段階）
```
【Phase 1】国内基盤構築（現在）
├── note: 日本語コンテンツ蓄積
├── Instagram/X/YouTube: 日本語メイン
└── LINE: 国内会員向け

【Phase 2】多言語展開（今後）
├── Medium: 英語記事（noteの翻訳版）
├── Instagram: 日英併記キャプション
├── YouTube: 字幕・翻訳タイトル追加
└── X: 英語ハッシュタグ追加
```

### 次回やること
- [ ] noteプロフィール設定（アイコン、自己紹介、URL）
- [ ] note初回記事投稿
- [ ] Medium アカウント作成検討

### 開設済みSNSアカウント一覧
| プラットフォーム | アカウント | 状態 |
|-----------------|-----------|------|
| Instagram | @harmonicscience_jp | 開設済み |
| X | @SFH_Science | 開設済み |
| LINE公式 | @868hqnfw | 開設済み |
| note | サウンドヒーリング協会 | **本日開設** |

---

## 2026-02-24（ミーティング議事録確認・海外展開追加）

### 実施内容
- NotebookLMで新規ミーティング議事録を確認
- 海外展開をPhase 11としてタスクシートに追加
- 将来目標・参考情報セクションを追加

### ミーティング議事録要点（Sound Healing Association Marketing Strategy）

#### 1. 広報戦略（SNS・NotebookLM活用）
- **信頼性向上**: 医療関係者のバックアップ、訴訟・事故ゼロの実績を前面に
- **体験談公開**: 薬機法に配慮しつつ実例を発信
- **既存コンテンツ再利用**: CD付き書籍など過去コンテンツをSNSで公開

#### 2. NotebookLM活用アイデア
- 長時間動画（2時間等）を要約 → SNS宣伝文句に活用
- 協会の資料フォルダを公開 →「自由に使ってください」形式

#### 3. 新規ターゲット拡張
- **海外発信**: イタリア、ウズベキスタン、台湾など既に需要あり → 英語化検討
- **法人向け（BtoB）**: ホンダ、パナソニック、第一興商との関係活用 → 企業向けワークショップ

### 更新ファイル
- タスクシート_SNS収益化.md: Phase 11（海外展開）追加、将来目標セクション追加

---

## 2026-02-24（コンテンツ制作完了）

### 実施内容
- 3ヶ月分の全SNSコンテンツ下書き作成完了
- 2セッション並行作業体制を構築

### 作成ファイル（コンテンツ/フォルダ）

| ファイル | 内容 | 本数 |
|----------|------|------|
| X投稿90本.md | 科学データ・名言・告知・シェア | 90本 |
| Instagram投稿48本.md | カルーセル・単画像・リール・告知 | 48本 |
| note記事12本.md | 無料8本・有料4本 | 12本 |
| LINEステップ配信7通.md | 登録〜7日目の自動配信 | 7通 |
| YouTube動画24本.md | BGM・解説・実践・イベント | 24本 |

### コンテンツ総数
- **合計: 181本 + LINE7通**
- すべて資料まとめ_API処理結果.mdの科学データを活用
- ターゲット（40-60代女性）を意識した内容

### YouTube動画構成
| カテゴリ | 本数 | 特徴 |
|----------|------|------|
| 自然音BGM（長尺） | 6本 | 1〜3時間、再生時間稼ぎ |
| 解説・教育 | 8本 | 台本付き |
| 実践ガイド | 6本 | 一緒にやる形式 |
| イベント記録 | 4本 | ダイジェスト |

### 次のステップ
- 別セッションでSNSアカウント開設進行中
- コンテンツの最終調整・画像制作
- 投稿スケジューラー設定

---

## 2025-02-24

### 実施内容
- SNS収益化フローチャートを再作成・提示
- 投稿頻度と3ヶ月分コンテンツ量を算出
- YouTube立ち上げプランを策定
- mocca-projectのタスク管理形式を参考にプロジェクト構造を整備

### 作成ファイル
1. **タスクシート_SNS収益化.md**
   - 全体タスク管理（Phase 1-5）
   - プラットフォーム別コンテンツ量
   - KPI目標設定

2. **タスクシート_YouTube.md**
   - YouTube専用タスク管理
   - 24本の動画コンテンツ計画
   - 収益化ロードマップ

3. **PROJECT_STANDARDS.md**
   - ドキュメント構成ルール
   - タスク管理ルール
   - コンテンツ制作ルール

### 3ヶ月分コンテンツ量（確定）
| プラットフォーム | 頻度 | 本数 |
|------------------|------|------|
| X | 毎日 | 90本 |
| Instagram | 週4回 | 48本 |
| YouTube | 週2回 | 24本 |
| note | 週1回 | 12本 |
| LINE | 週1回 | 12本 |
| **合計** | | **186本** |

### 成果
- プロジェクト管理構造がmocca-project形式に統一
- Phase別タスク分解により作業分担が可能に

### 次のステップ
- Phase 1: 各プラットフォームアカウント開設
- Phase 2: コンテンツ一括制作開始

---

## 2025-02-24（追加作業）

### 実施内容
- 代表・圭一郎さんとの会話内容を確認（NotebookLM音声記録）
- 長期目標・ビジョンをタスクシートに反映

### 圭一郎さんとの会話要点
1. **最終目標**: 資格を取得する実践者（セラピスト）を増やす
2. **ターゲット**: 40代〜60代女性（子育てを終えた層）
3. **核心メッセージ**: 病院に頼らず「自己回復力」を高める知恵
4. **ブランディング課題**: 「サウンドヒーリング」が怪しいと思われがち
5. **対策**: 科学的・歴史的根拠を前面に、既存書籍のデジタル化

### 成果
- タスクシート_SNS収益化.md に以下を追加：
  - メインターゲット（40-60代女性）
  - 長期目標セクション（Phase 6-10）
  - ブランディング方針

### 追加したPhase（今後の目標）
| Phase | 内容 | 時期 |
|-------|------|------|
| Phase 6 | 体験会誘導強化 | Month 4-6 |
| Phase 7 | 継続学習コミュニティ構築 | Month 6-9 |
| Phase 8 | スキルアップ体系化 | Month 9-12 |
| Phase 9 | 資格制度準備 | Year 2 |
| Phase 10 | 実践者ネットワーク拡大 | Year 2-3 |

---

## 2025-02-23

### 実施内容
- 2022年〜2025年の協会誌PDF読み込み状況を確認
- 資料まとめ.mdに既に2022年〜2025年の情報が整理済みであることを確認

### 確認した協会誌（2022年〜2025年）
1. **vol32-33 (2021年 20周年記念号)** - 目次・活動実績まとめ
2. **vol34-35 (2022年)** - 「地球の声に耳を傾けよう」
   - 変革期の自分軸、トランスパーソナルセルフ、音の糧
3. **vol35-36 (2023年)** - 「かんむり座のカムイとうしかい座のアルクトゥルス」
   - 中村泰治会長逝去、スターライトヒーリングの歴史
4. **vol37-38 (2024年)** - 「自分を信じる時代」
   - 研修会実績、日本の医療費問題、OECD比較データ
5. **vol39-40 (2025年)** - 「私たちに満ちる大自然の力を育もう」
   - 宇宙と天体、音の振動原理、新しい周期の到来

### 成果
- 資料まとめ.mdは2011年〜2025年の協会誌情報が完備
- SNS投稿用の画像情報も整理済み

### 次のステップ
- SNSコンテンツの作成開始

---

## 2025-02-23（追加作業）

### 実施内容
- サブフォルダ内の未処理資料を確認・処理
- 資料まとめ_API処理結果.mdに追記

### サブフォルダ構成（171ファイル）
1. **2.10 -1　　４３本/**
   - 音の効果事例体験談１７本
   - 原稿　様々１５本
   - 雑誌ほかメディア５本
   - CD　MuAtsu CD　６本

2. **2.10 -2　５２本/**
   - 骨密度４本
   - 体感音響１５本
   - 自然音実験エビデンス１６本
   - ポスターほか１4本

3. **2.9 　58本/**
   - スターライトヒーリング２２本
   - CD book 本３６本

### 追加処理した重要資料

#### 実験・エビデンス系
1. **水道水に60分自然音を聞かせる実験（2021年）**
   - 東洋化学株式会社 中島俊樹
   - 400倍拡大画像で水の構造変化を視覚化
   - 残留塩素の害作用を解除

2. **植物に及ぼす自然音の効果（2008年）**
   - 第25回生命情報科学シンポジウム
   - 奥健夫、喜田圭一郎、中村泰治
   - 菊の花48日間実験：自然音で生命力維持

3. **自律神経機能への影響（2016年）**
   - 被験者9名（12歳〜48歳）
   - 副交感神経・交感神経両方の機能向上を確認

4. **骨密度への影響（2012年）**
   - 田園調布 長田整形外科
   - 6ヶ月後の骨密度上昇を確認（70代・80代女性）

#### イベント系
5. **スターライトヒーリング マラマハワイ（2024年）**
   - さいたま市宇宙劇場
   - 累計1,400名以上来場
   - ハワイ州観光局後援

### 成果
- 資料まとめ_API処理結果.mdにサブフォルダ資料を追記完了
- SNS活用に最適なエビデンス資料を特定

---

## 2025-02-06

### 実施内容
- 資料フォルダ内の協会誌PDF（2011年〜2021年）を読み込み
- 資料まとめ.md を作成（重要情報を整理）

### 読み込んだ資料
1. 2011協会誌p2-p3.pdf - Peace Creating Trip to New York
2. 2012P2-P3_喜田sam3.pdf - 言葉と音の力
3. 2013 vol16-17_P2-P3_sam1.pdf - 自分の維新と攘夷
4. 2014 vol18-19_P2-P3_.pdf - 私のウエルビーイングライフ（喜田氏自伝）
5. 2015 P2-P3_Harmonic Revolution 2015.pdf - 3つのメソッド詳細
6. 2016協会誌P2-P3.pdf - 新しい生き方（ゲイナー博士逝去報告）
7. 2017 vol24-25 和らかい心と柔らかな体.pdf - ホクレア号、アカカさん
8. 2018自分を動かす力.pdf - 日野原先生との関係、カリブ海クルーズ
9. 2019 sh_vol28-29_data_P2-P3_sam3.pdf - 会社設立の歴史詳細
10. 2020 p2-p3 Journal vol30-31.pdf - ライフフォース概念
11. 2021 SH協会20周年 p4-5.pdf - 20周年挨拶

### 成果
- 資料まとめ.md に以下を整理：
  - 会社・団体の歴史年表
  - 喜田圭一郎理事長プロフィール
  - 3つのメソッドの詳細
  - 重要人物（ゲイナー博士、日野原先生、アカカさん等）
  - 理念・コンセプト
  - 引用される思想家・研究者一覧
  - キーワード・フレーズ

### 残り資料
- 2022年〜2025年の協会誌PDF（6ファイル）
- 2008年〜2010年のdocファイル（3ファイル、バイナリで読み込み不可）

---

## 2025-02-05

### 実施内容
- プロジェクト初期セットアップ
- GitHubルール（CLAUDE_INSTRUCTION.md）の確認
- サウンドヒーリング協会サイト（https://www.sound-healing.jp/）の調査
  - サイト構造、メニュー、コンテンツの把握
  - 定期イベント情報の確認
  - 既存メディア（YouTube、Facebook、協会誌）の確認
- ジョイファンデーションサイト（https://www.h-garden.com/）の調査
  - 会社概要、事業内容の把握
  - 製品情報（小型体感音響）の確認
  - 取引先情報の確認

### 成果
- 両団体の関係性を理解
  - NPO: 理念・研究・教育
  - 株式会社: 製品化・商用サービス
- 広報に活用できるコンテンツの把握
  - 定期イベント（Harmonic Day、ここちよい音の日など）
  - 製品（小型体感音響 Harmonic Massage）
  - スターライトヒーリング マラマハワイ
- プロジェクト基盤ファイル作成（README.md、CLAUDE.md、DEVLOG.md）

### 課題・備考
- SNS戦略の具体的な計画策定が必要
- 公式LINE構築の検討
- 投稿コンテンツのテンプレート作成が必要
