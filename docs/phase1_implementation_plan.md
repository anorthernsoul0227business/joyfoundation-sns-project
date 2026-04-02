# Phase 1 実装深掘り（Issue粒度 + 実装設計）

最終更新: 2026-04-02

本ドキュメントは、以下3ファイルの内容を前提に Phase 1（Python一本化 + Google Sheetsマスター + IG画像lh3 PoC）を実装可能な粒度に落とし込んだものです。

- `docs/codex_briefing.md`
- `docs/auto_poster_design.md`
- `x_auto_poster.py`

---

## 1. GitHub Issue 化（そのまま起票できる粒度）

> フォーマット: **Title / Description / Acceptance Criteria / Dependencies / Critical Path**

### Issue 1: Phase1-01 リポジトリ基盤整備（Python実行基盤 + ディレクトリ再編）

**Description**
- `x_auto_poster.py` 単体構成をモジュール分割しやすい構造へ移行する。
- 最低限、以下配置を用意する。
  - `sns_auto_poster.py`（エントリーポイント）
  - `sheet_manager.py`
  - `image_handler.py`
  - `x_poster.py`
  - `ig_poster.py`
  - `shared_types.py`（dataclass / enum）
- ログ出力先を `logs/` に統一し、実行ID（run_id）でトレース可能にする。

**Acceptance Criteria**
- [ ] `python sns_auto_poster.py --help` が実行できる。
- [ ] import 循環がない。
- [ ] 既存の `x_auto_poster.py --dry --list --post` 相当のCLIが新エントリーに定義される。

**Dependencies**
- なし（最初に着手）

**Critical Path**
- 1/8

---

### Issue 2: Phase1-02 Google Sheets 読み書き層（sheet_manager.py）実装

**Description**
- `X投稿v2` と `Instagram` シートの共通アクセス層を作る。
- ステータス `投稿予約` のみ抽出。
- 投稿日時判定ルール:
  - `now >= scheduled_at`
  - `scheduled_at >= now - 24h`
- 投稿結果を M/L/O 列（または IG側の対応列）へ反映。

**Acceptance Criteria**
- [ ] 2シートの「投稿予約」行を `ScheduledPost` として取得できる。
- [ ] 成功時: `投稿済み` + 投稿ID + 投稿日時をメモに記録。
- [ ] 失敗時: `投稿失敗` + エラー要約をメモに記録。
- [ ] dry-run時はシート更新しない。

**Dependencies**
- Phase1-01

**Critical Path**
- 2/8

---

### Issue 3: Phase1-03 画像取得・変換層（image_handler.py）実装

**Description**
- Google Drive URLからファイルID抽出。
- X向け/IG向けのリサイズ（X: 1200x675 or 1200x1200、IG: 1080x1350）。
- JPEG品質を段階的に下げ容量制限へ収める。
- 失敗時は「画像なし投稿可否」を呼び出し元へ返せるよう結果型で返す。

**Acceptance Criteria**
- [ ] Drive URL / lh3 URL / 直接URLの3系統を解決できる。
- [ ] 画像変換失敗時に例外を握りつぶさず、分類済みエラーで返る。
- [ ] 同一URLの重複ダウンロードを避ける（1 run 内キャッシュ）。

**Dependencies**
- Phase1-01

**Critical Path**
- 3/8（X/IG双方の投稿品質に直結）

---

### Issue 4: Phase1-04 X投稿層（x_poster.py）実装 + 既存コード置換

**Description**
- 既存 `x_auto_poster.py` の `upload_image_to_x` / `post_tweet` を分離。
- APIエラーをHTTPコード別に分類して返す。
- 画像投稿失敗時、設定に応じてテキストのみ投稿フォールバック。

**Acceptance Criteria**
- [ ] media upload(v1.1) + post(v2) が実行できる。
- [ ] 401/403は即失敗、429/5xxはリトライ対象。
- [ ] 成功時 `platform_post_id`（Tweet ID）を返却。

**Dependencies**
- Phase1-02
- Phase1-03

**Critical Path**
- 4/8

---

### Issue 5: Phase1-05 IG投稿層（ig_poster.py）実装（単画像PoC + フォールバック）

**Description**
- Graph API Container方式で単画像投稿を実装。
- `image_url` は lh3 URL（`https://lh3.googleusercontent.com/d/{file_id}`）を第一候補。
- コンテナ作成失敗時は明示的に `投稿失敗` とし自動リトライしない。

**Acceptance Criteria**
- [ ] `/media` -> `/media_publish` の2段階が動作する。
- [ ] コンテナステータス待機（FINISHED）ロジックあり。
- [ ] 投稿成功時 `creation_id` / `ig_media_id` を記録。

**Dependencies**
- Phase1-02
- Phase1-03

**Critical Path**
- 5/8

---

### Issue 6: Phase1-06 オーケストレーター（sns_auto_poster.py）実装

**Description**
- X/IG共通でジョブ実行し、結果を集約。
- CLI:
  - `--dry-run`
  - `--platform x|ig|all`
  - `--max-posts N`
  - `--since-minutes`
- 排他制御（同時実行防止）を実装。

**Acceptance Criteria**
- [ ] dry-runで外部API呼び出しなし。
- [ ] platform絞り込み可能。
- [ ] エラーがあっても他行処理を継続し、最後にサマリ終了コードを返す。

**Dependencies**
- Phase1-02
- Phase1-04
- Phase1-05

**Critical Path**
- 6/8

---

### Issue 7: Phase1-07 GitHub Actions 本番ワークフロー導入

**Description**
- Python実行workflowを追加。
- `workflow_dispatch` で dry-run を選択可能にする。
- SecretからGoogle SA JSONを復元して実行。

**Acceptance Criteria**
- [ ] schedule + manual dispatch が両方動作。
- [ ] dry-runでSheetステータスは更新されない。
- [ ] 失敗時にログがartifactとして取得できる。

**Dependencies**
- Phase1-06

**Critical Path**
- 7/8

---

### Issue 8: Phase1-08 運用Runbook（X権限変更 / トークン更新 / 障害時対応）

**Description**
- X Developer Portal の権限修正手順をRunbook化。
- `.env` / GitHub Secrets更新手順を明文化。
- 障害時一次切り分け表（認証/画像/レート制限）を追加。

**Acceptance Criteria**
- [ ] 手順書のみで権限更新〜再デプロイが可能。
- [ ] 投稿失敗時の復旧フロー（人手で投稿予約に戻す）が明文化。

**Dependencies**
- Phase1-07

**Critical Path**
- 8/8

---

### クリティカルパス（実装順）

1. Phase1-01 基盤整備  
2. Phase1-02 Sheets層  
3. Phase1-03 画像層  
4. Phase1-04 X投稿層  
5. Phase1-05 IG投稿層  
6. Phase1-06 オーケストレーター  
7. Phase1-07 Actions本番化  
8. Phase1-08 Runbook整備

---

## 2. `sns_auto_poster.py` モジュール設計

### 2-1. `x_auto_poster.py` 読解に基づくリファクタリング方針

現状の `x_auto_poster.py` は以下を1ファイルに内包している。

- 設定（定数・列定義）
- 認証生成
- Sheets I/O
- 画像DL + Xアップロード
- 投稿実行
- ステータス更新
- CLI

このため、テスト観点で「Sheets境界」「X API境界」「純粋ロジック」が分離されていない。Phase 1では以下方針で分解する。

1. **境界分離**: 外部I/O（Sheets/API）と純粋ロジックを分離。  
2. **戻り値の型統一**: `PostResult` / `ErrorCategory` を導入。  
3. **例外戦略統一**: モジュール内で例外を分類し、上位でハンドリング。  
4. **CLI最小化**: `sns_auto_poster.py` は引数解釈と orchestration のみ。

### 2-2. インターフェース定義（推奨シグネチャ）

```python
# shared_types.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

Platform = Literal["x", "ig"]

class ErrorCategory(str, Enum):
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    BAD_REQUEST = "bad_request"
    SERVER = "server"
    IMAGE = "image"
    SHEET = "sheet"
    UNKNOWN = "unknown"

@dataclass
class ScheduledPost:
    row: int
    platform: Platform
    text: str
    image_urls: list[str]
    scheduled_at: datetime | None
    status: str

@dataclass
class PostResult:
    ok: bool
    platform_post_id: str | None
    error_category: ErrorCategory | None
    error_message: str | None
```

```python
# sheet_manager.py
from datetime import datetime
from typing import Iterable
from shared_types import ScheduledPost, PostResult

def get_worksheet(spreadsheet_id: str, sheet_name: str): ...

def fetch_scheduled_posts(
    spreadsheet_id: str,
    sheet_name: str,
    now: datetime,
    max_age_hours: int = 24,
) -> list[ScheduledPost]: ...

def mark_post_result(
    spreadsheet_id: str,
    sheet_name: str,
    row: int,
    result: PostResult,
    posted_at: datetime,
) -> None: ...

def append_memo(
    spreadsheet_id: str,
    sheet_name: str,
    row: int,
    message: str,
) -> None: ...
```

```python
# image_handler.py
from dataclasses import dataclass
from typing import Literal

Target = Literal["x_landscape", "x_square", "ig_feed"]

@dataclass
class PreparedImage:
    local_path: str
    width: int
    height: int
    mime_type: str
    bytes_size: int


def extract_drive_file_id(url: str) -> str | None: ...

def build_lh3_url(file_id: str) -> str: ...

def download_image(url: str, timeout_sec: int = 30) -> bytes: ...

def resize_for_target(raw: bytes, target: Target) -> PreparedImage: ...

def prepare_images_for_platform(
    image_urls: list[str],
    platform: Literal["x", "ig"],
) -> list[PreparedImage]: ...
```

```python
# x_poster.py
from shared_types import PostResult
from image_handler import PreparedImage

def post_to_x(
    text: str,
    images: list[PreparedImage],
    allow_text_only_fallback: bool = True,
) -> PostResult: ...
```

```python
# ig_poster.py
from shared_types import PostResult

def create_media_container(image_url: str, caption: str) -> str: ...

def wait_container_finished(
    container_id: str,
    timeout_sec: int = 120,
    interval_sec: int = 5,
) -> bool: ...

def publish_media(container_id: str) -> str: ...

def post_to_instagram(
    caption: str,
    image_url: str,
) -> PostResult: ...
```

### 2-3. エラーハンドリング実装パターン

#### パターンA: HTTPコード分類 + Result返却
- 401/403: `AUTH`
- 429: `RATE_LIMIT`
- 400: `BAD_REQUEST`
- 5xx: `SERVER`
- 接続失敗/timeout: `NETWORK`

#### パターンB: 画像失敗時フォールバック
- X: 画像失敗でも `allow_text_only_fallback=True` ならテキスト投稿を試行
- IG: 画像必須のため即 `IMAGE` 失敗

#### パターンC: Sheet更新の安全化
- 投稿APIが成功してからステータス更新
- 更新失敗時はリトライ3回（指数バックオフ）
- それでも失敗ならログに `SHEET_UPDATE_FAILED` を明示

#### パターンD: 行単位隔離
- 1行失敗しても全体停止しない
- 最後に「成功件数/失敗件数」を返却

---

## 3. GitHub Actions ワークフロー完成版

実ファイル: `.github/workflows/auto_post.yml`

### Secrets設定手順（service_account.json Base64方式）

1. ローカルでBase64化（改行なし）
   - macOS:
     - `base64 -i ~/.config/gspread/service_account.json | tr -d '\n'`
   - Linux:
     - `base64 -w 0 ~/.config/gspread/service_account.json`
2. GitHub > Repository > Settings > Secrets and variables > Actions > New repository secret
3. `GOOGLE_SERVICE_ACCOUNT_JSON_B64` として貼り付け
4. ワークフロー内で decode:
   - `echo "$GOOGLE_SERVICE_ACCOUNT_JSON_B64" | base64 -d > ~/.config/gspread/service_account.json`

### cron schedule最適化

- 投稿時間帯が 20:00-22:00 JST 中心のため、毎時実行ではなく「高頻度時間帯 + 低頻度補完」に分離。
- 採用案（UTC）:
  - `0 11 * * *` (JST 20:00)
  - `0 12 * * *` (JST 21:00)
  - `0 13 * * *` (JST 22:00)
  - `0 0 * * *`  (JST 09:00 取りこぼし補完)

### dry-run組み込み

- `workflow_dispatch` で `dry_run: true|false` を選択。
- dispatch時 `dry_run=true` なら `--dry-run` で実行。
- schedule時は本番投稿（`dry_run=false`）固定。

---

## 4. lh3 IG画像URL PoC検証コード

実ファイル: `scripts/verify_lh3_ig_url.py`

### 検証観点

1. Drive URLから `file_id` 抽出できるか
2. `https://lh3.googleusercontent.com/d/{file_id}` がHTTP 200系で取得可能か
3. `Content-Type` が `image/*` か
4. （任意）IG Graph API `/media` でコンテナ作成可能か

### 実行例

```bash
python scripts/verify_lh3_ig_url.py \
  --drive-url "https://drive.google.com/file/d/FILE_ID/view?usp=sharing"

# IG APIまで含めて検証
python scripts/verify_lh3_ig_url.py \
  --drive-url "https://drive.google.com/file/d/FILE_ID/view?usp=sharing" \
  --ig-user-id "$IG_BUSINESS_ACCOUNT_ID" \
  --ig-access-token "$IG_ACCESS_TOKEN" \
  --check-ig-api
```

---

## 5. X API権限修正手順書（Read/Write化）

### 5-1. Developer Portal操作

1. X Developer Portalへログイン
2. 対象 Project/App を開く
3. **User authentication settings** を開く
4. App permissions を **Read and write** に変更
5. 保存して反映

> 注意: 既存のAccess Tokenは旧権限のままのため、再生成が必要。

### 5-2. Access Token再生成

1. App画面の Keys and tokens を開く
2. Access Token / Secret を **Regenerate**
3. 新しい `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` を控える

### 5-3. `.env` 更新手順

```bash
# 例: ローカル .env
X_CONSUMER_KEY=...
X_CONSUMER_SECRET=...
X_ACCESS_TOKEN=NEW_TOKEN
X_ACCESS_TOKEN_SECRET=NEW_SECRET
```

反映確認:

```bash
python x_auto_poster.py --dry
```

### 5-4. GitHub Secrets更新

- `X_CONSUMER_KEY`
- `X_CONSUMER_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

更新後、`workflow_dispatch` で dry-run 実行し、403が解消されたことを確認する。
