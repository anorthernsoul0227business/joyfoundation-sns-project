# Codexブリーフィング: WEB-020 X投稿Publisher実装

**作成日**: 2026-04-21
**担当Issue**: WEB-020（Sprint 3 / 工数: 1.5日）
**依存**: WEB-018（SNSアカウント連携API / コミット済 `e4b5d22`）
**参考**: プロジェクト直下の既存実装 `x_auto_poster.py`
**後続**: WEB-022（Celeryで `publish_post` タスクから呼ぶ）

---

## タスク概要

FastAPI 側に **X (Twitter) 投稿 Publisher** を実装する。`posts` / `post_targets` / `post_media` / `sns_accounts` からデータを読み、X API で実投稿を行い、結果を `post_targets` に書き戻す純粋なサービス層。

Google Sheets 依存の既存 `x_auto_poster.py` をロジック参考とし、Supabase テーブルベースに置き換える。**WEB-020 はサービス層とユニットテストのみを実装する**。Celery タスク・REST エンドポイント・フロントUIは WEB-022 以降。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| 呼び出し方 | `publish_target(target_id: UUID) -> PublishResult` 関数を公開 | WEB-022 の Celery タスクから呼ぶ純粋関数 |
| 認証 | `sns_accounts.access_token` を `{oauth_token}:{oauth_token_secret}` としてパースし OAuth1 組立 | WEB-018 の保存形式に合わせる |
| 画像取得 | `post_media.storage_path` を **HTTP URL として GET**（R2 公開URL前提） | Phase 1 の R2 運用と整合。Supabase Storage 経由は WEB-024 |
| Consumer Key/Secret | `settings.x_consumer_key` / `x_consumer_secret` | WEB-018 で config 追加済み |
| HTTP | `requests` + `requests_oauthlib.OAuth1` | 既存 `x_auto_poster.py` と同じ。追加依存不要 |
| エラー分類 | 4xx 認可系は即失敗、5xx/ネットワークは同エンドポイント内で完結 | 既存実装を踏襲。Phase 1 で自動リトライはしない |
| ログ | 秘密情報（token, secret）は出力しない。tweet_id / http status / request_id のみ | WEB-018 の OAuth 同様の原則 |
| テスト | `responses` or `requests-mock` で外部HTTPをモック。Supabaseクライアントはフェイク差し替え | 既存 `tests/api/test_sns_accounts.py` と同方針 |

### Publisher 抽象クラス

```python
# apps/api/app/services/publisher/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PublishResult:
    success: bool
    platform_post_id: str | None
    error_message: str | None
    extra: dict[str, Any] | None = None  # 後続で reply_id 等を載せる用

class Publisher(ABC):
    platform: str

    @abstractmethod
    def publish(
        self,
        *,
        text: str,
        image_urls: list[str],
        account: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> PublishResult:
        """実SNSに投稿し結果を返す。例外は内部で握りつぶしてPublishResultに包む。"""
```

---

## スコープ（WEB-020で実装するもの）

### 1. 新規パッケージ: `apps/api/app/services/publisher/`

```
apps/api/app/services/publisher/
├── __init__.py          # get_publisher(platform) ファクトリ
├── base.py              # Publisher 抽象クラス + PublishResult
├── x_publisher.py       # X OAuth1.0a 実装
└── orchestrator.py      # publish_target(target_id) — DB読み書き + Publisher呼び出し
```

### 2. `x_publisher.py` 仕様

既存 `x_auto_poster.py` の `upload_image_to_x` / `post_tweet` をベースに、Publisher インターフェース準拠で書き直す:

- **コンストラクタ**: consumer_key / consumer_secret を受け取る
- `publish(text, image_urls, account, options=None)`:
  - `account["access_token"]` を `:` で split → `(oauth_token, oauth_token_secret)`
  - OAuth1 オブジェクト構築（consumer + user）
  - 各 image_url を GET → X の `upload.twitter.com/1.1/media/upload.json` に multipart POST → `media_id_string` 収集
  - `api.x.com/2/tweets` に `{"text": ..., "media": {"media_ids": [...]}}` を POST
  - 成功: `PublishResult(success=True, platform_post_id=tweet_id, error_message=None)`
  - 失敗: `PublishResult(success=False, platform_post_id=None, error_message=<短いsummary>)`
  - 例外は全て握りつぶして PublishResult にラップ
- `options`:
  - `reply_to: str` が入っていれば `reply.in_reply_to_tweet_id` を付与
  - Phase 1 では `reply_to` のみサポート（既存コードにもあるリプライ対応）
- エンドポイントは `api.x.com/2/tweets` を固定で使用。`api.twitter.com` フォールバックは Phase 1 では**不要**（既存システムは残っているため実運用で検証済）
- 認可系エラー (400/401/402/403) と 4xx/5xx の区別は `error_message` に status code を含める程度で OK
- **秘密情報をログに書かない**: tweet_id / status / request_id のみ

### 3. `orchestrator.py` 仕様

`publish_target(target_id: UUID) -> PublishResult` を公開:

1. `post_targets` 1 行取得（id=target_id）
   - なければ `HTTPException 404`（Celery 側が握る想定なので例外 OK）
   - すでに `status in ('published','skipped')` ならノーオペで成功相当 return
2. 親 `posts` 取得（post_id=target.post_id）
3. `post_media` を `sort_order ASC` で最大 4 件取得、`storage_path` を image_urls とする
   - 現状 `storage_path` は公開URL想定。`http` で始まらなければスキップしつつログ warning
4. `sns_accounts`（本体テーブル）から `org_id = post.org_id AND platform = target.platform AND is_active = true` を 1 件取得
   - 複数 handle がある場合は `created_at DESC` 優先（WEB-019 UI は複数接続を想定、Phase 1 は1件選択）
   - なければ `PublishResult(success=False, error_message="No active X account connected")` 相当で `post_targets.status='failed'` にする
5. `post_targets.status = 'publishing'` に UPDATE（Celery 二重実行対策）
6. `get_publisher("x")` で X Publisher を取得、`publish(...)` 呼び出し
7. 結果を反映:
   - 成功時: `post_targets.status='published', published_at=now, platform_post_id=<tweet_id>, error_message=NULL`
   - 失敗時: `post_targets.status='failed', error_message=<truncated to 500 chars>`
8. 全 `post_targets` が `published` になったら親 `posts.status='published', published_at=now` に UPDATE
9. `PublishResult` を return

Supabase アクセスは **`app.core.supabase.get_supabase_client` 経由**のみ。

### 4. `__init__.py` - ファクトリ

```python
# apps/api/app/services/publisher/__init__.py
from .base import Publisher, PublishResult
from .x_publisher import XPublisher

def get_publisher(platform: str) -> Publisher:
    if platform == "x":
        from app.config import get_settings
        s = get_settings()
        if not s.x_consumer_key or not s.x_consumer_secret:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=500, detail="X consumer credentials not configured")
        return XPublisher(consumer_key=s.x_consumer_key, consumer_secret=s.x_consumer_secret)
    raise NotImplementedError(f"Publisher for platform '{platform}' is not implemented")
```

IG は WEB-021 で追加する。

### 5. テスト（`apps/api/tests/services/test_x_publisher.py` 新規 + `test_publisher_orchestrator.py` 新規）

#### `test_x_publisher.py`
- `responses` or `requests_mock` (既に pyproject.toml に無ければ dev dep として追加) で外部HTTPモック
- 成功ケース: media upload → tweets POST → PublishResult.success=True, platform_post_id=正しいID
- 画像0枚: media upload呼ばれず tweet 成功
- media upload 失敗: そのままスキップ（既存挙動踏襲、PublishResult は success=True で残media_ids投稿）
- tweet POST 401: success=False, error_message に 401 含む
- tweet POST 500: success=False
- ネットワーク例外 (`requests.ConnectionError`): success=False
- **secret が account に含まれていない**: success=False, 分かりやすい error
- token パース不正（`:` 無し）: success=False

#### `test_publisher_orchestrator.py`
- Supabase クライアントをフェイクに差し替え（既存 `tests/api/test_sns_accounts.py` の InMemoryAccountStore 方式）
- `publish_target` が post / target / media / sns_account を正しく読む
- 成功時 `post_targets` が published になる
- 複数 targets のうち1つが成功1つが既 published → 親 `posts` が published になる
- 未接続アカウント → post_targets.status='failed', error_message に "No active" が入る
- すでに publishing 中 → 冪等性の簡易テスト（再入したら何もしない or PublishResult 直返し）
- 例外時も DB 更新が完結する（finally 相当の挙動）

既存テスト 18 passed / 44 skipped を下回らないこと。新規テストは実DB不要の mock 方式で **全てが passed 化**されるよう作ること。

### 6. OpenAPI

**このIssueではAPI追加なし**。OpenAPI 再生成は不要。

### 7. 依存追加

- `requests` はすでに transitive で入っている想定。未入なら `poetry add requests@^2.31`
- テストで `requests_mock` or `responses` を使う場合 `poetry add --group dev requests-mock@^1.12` or `responses@^0.25`
  - **推奨**: `responses`（既存 `httpx` と併存可能、メンテ活発）
- サンドボックスで `poetry add` が失敗したら **偽装禁止**、pyproject.toml に手動で版指定を追記するに留め Claude 側で `poetry install` を実行する（Codex が sandbox の場合）

### 8. README 更新

`apps/api/README.md` に以下を追加:
- Publisher アーキテクチャ概要（抽象→具象→orchestrator）
- `publish_target(target_id)` のシグネチャ
- 実投稿検証手順（Claude 手動検証用）

---

## スコープ外（やらないこと）

- ❌ Instagram Publisher（WEB-021 で別 Issue）
- ❌ Celery タスク `publish_post` の実装（WEB-022）
- ❌ REST エンドポイントからの即時投稿トリガ（既存 `/api/posts/{id}/publish-now` は DB 状態を変えるだけの Stub。実投稿接続は WEB-022）
- ❌ Supabase Storage からの画像ダウンロード（WEB-024。Phase 1 は公開URL想定）
- ❌ メディアアップロードの並列化・リトライ（Phase 1 はシリアル）
- ❌ Rate limit 対応（X Free tier は 1日17件前後。Phase 1 は上限監視なし）
- ❌ フロントエンド表示の更新（WEB-027 の通知で対応）
- ❌ トークンの at-rest 暗号化 / IG 長期トークンリフレッシュ
- ❌ reply chain（リプライツリー）の自動構築 — `options.reply_to` で単発リプライのみサポート
- ❌ スレッド投稿（複数 tweet 連投）
- ❌ `notifier.py` の移植（WEB-023 で別 Issue）

---

## 必須検証コマンド

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# 依存追加後
cd apps/api && poetry install

# 既存+新規 pytest 全通過
poetry run pytest

# ruff / lint
poetry run ruff check .

# フロント側影響なし確認
cd ../.. && pnpm typecheck && pnpm build
```

---

## 絶対守るべきこと

- **CLAUDE.md Codex CLI Usage 節の偽装禁止ルール**: `responses` や `requests-mock` が入らない場合でも偽装せず、`pyproject.toml` に依存を書くだけで Claude 側で `poetry install` する前提で進める
- **秘密情報をログ出力しない**（access_token / access_token_secret / consumer_secret）
- **`sns_accounts.access_token` の構造（`:` 区切り）を破壊しない**。パース失敗時はエラー扱い
- **`app.core.supabase.get_supabase_client` 経由**のみで DB アクセス。新規 Supabase クライアント初期化禁止
- **既存 `x_auto_poster.py` は触らない**（プロジェクト直下で引き続き稼働中）
- **既存 `apps/api/app/services/sns_accounts.py` 等 WEB-018 成果物は触らない**
- **`apps/web/` 変更禁止**（このIssueはバックエンドのみ）
- **Finder 複製 `* 2.*` を作らない**
- **`packages/` 配下や `apps/api/app/` 直下に npm/PyPI 公式名と衝突する偽装 shim を作らない**
- **既存 pytest (18 passed / 44 skipped) を維持**し、新規テストは全て `passed` で追加する
- **本番 Supabase / 本番 X API に実呼び出ししない**。テストは全て mock。実投稿検証は Claude が `.env` 整備後に手動実施

---

## 成果物チェックリスト

- [ ] `apps/api/app/services/publisher/__init__.py` 新規（`get_publisher` ファクトリ）
- [ ] `apps/api/app/services/publisher/base.py` 新規（`Publisher` ABC + `PublishResult`）
- [ ] `apps/api/app/services/publisher/x_publisher.py` 新規
- [ ] `apps/api/app/services/publisher/orchestrator.py` 新規（`publish_target`）
- [ ] `apps/api/pyproject.toml` にテスト用 HTTP モック依存 (`responses` 推奨) を追加
- [ ] `apps/api/tests/services/` ディレクトリ新規 + `__init__.py`
- [ ] `apps/api/tests/services/test_x_publisher.py` 新規（8 ケース以上）
- [ ] `apps/api/tests/services/test_publisher_orchestrator.py` 新規（5 ケース以上）
- [ ] `apps/api/README.md` に Publisher 節追加
- [ ] `poetry install` 後に `poetry run pytest` で 18 + 新規 >= 13 件追加 = **31+ passed** 想定
- [ ] `poetry run ruff check .` 全通過
- [ ] `pnpm typecheck` 成功（影響なし確認）
- [ ] 偽装・shim・Finder複製 一切なし
- [ ] スコープ外の実装混入なし（IG / Celery / endpoint / storage download 等）

---

## コミット指示

- `git add` は明示指定のみ
- `.env` / `poetry.lock` のキャッシュ以外はコミット対象外
- 生成物 `apps/web/src/generated/` は触らない
- コミットメッセージ: `feat: WEB-020 X投稿Publisher実装`
- Co-Authored-By 不要（Claude 側で最終コミット時に付与する）

---

## 補足: 関連設計ドキュメント / コード

- `design/design/IMPLEMENTATION_PLAN.md` L647 WEB-020 定義
- `design/design/PLATFORM_MATRIX.md` L41-43 X 認証方式・エラー挙動
- `sns-calendar-app/supabase/migrations/20260420010431_posts_schema.sql` — posts / post_targets / post_media / sns_accounts 列構造
- `x_auto_poster.py` L71-210 — 既存 X 投稿ロジックの参考実装
- `apps/api/app/services/oauth_x.py` — WEB-018 で追加した OAuth1 トークン交換（ここと整合するアクセストークン形式）
- `apps/api/app/services/sns_accounts.py` `upsert_sns_account` — access_token = `{oauth_token}:{oauth_token_secret}` 保存形式

---

## 補足: 環境情報

- Python 3.12+ / Poetry 1.8+
- FastAPI 0.115+ / Supabase Python SDK v2
- `requests-oauthlib` 2.0.0（WEB-018 で導入済）
- テスト: `pytest` 8.x / `anyio`（既存）
- `responses` 新規導入推奨（`requests` モック用）

**Codex 側で実施**: コード実装 / pytest モック / ruff / pyproject.toml 依存追加。
**Claude 側で実施**: `poetry install` の実行（ネット到達）、`.env` 整備後の実投稿検証、WEB-022 着手時の Celery 呼び出し結線。
