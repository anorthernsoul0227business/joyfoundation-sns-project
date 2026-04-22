# Codexブリーフィング: WEB-021 Instagram投稿Publisher実装

**作成日**: 2026-04-21
**担当Issue**: WEB-021（Sprint 3 / 工数: 1.5日）
**依存**: WEB-018（SNSアカウント連携API）、WEB-020（Publisher抽象・orchestrator・ファクトリ）
**参考**: プロジェクト直下の既存実装 `ig_auto_poster.py`
**後続**: WEB-022（Celery `publish_post` から呼ぶ）

---

## タスク概要

FastAPI 側に **Instagram投稿 Publisher** を実装する。WEB-020 で作った `Publisher` 抽象に準拠し、`services/publisher/ig_publisher.py` として追加。Instagram Graph API の Container ベースの投稿フロー（単一画像・カルーセル両対応）を実装する。

既存 `ig_auto_poster.py` の R2 経由ホスティング + Container 作成 + 公開フローをそのまま踏襲する。WEB-020 と同じく **サービス層とユニットテストのみ**。Celery・REST・フロントは別 Issue。

---

## 前提: スキーマ拡張が必要

WEB-018 の `sns_accounts` には IG Business Account ID が保存されていない。Instagram Graph API の投稿エンドポイントは `POST /{ig_business_account_id}/media` なので必須。以下の拡張を本 Issue で行う。

### 1. マイグレーション追加: `sns_accounts.platform_account_id`

```sql
-- supabase/migrations/YYYYMMDDHHMMSS_sns_accounts_platform_id.sql
ALTER TABLE public.sns_accounts
  ADD COLUMN platform_account_id TEXT;

COMMENT ON COLUMN public.sns_accounts.platform_account_id IS
  'プロバイダー側のアカウントID。IG Business Account ID、X user_id 等、投稿APIで使う識別子';

-- sns_accounts_safe ビューには含めない（内部識別子のため）
```

**重要**: 既存 `sns_accounts_safe` VIEW は変更しない（platform_account_id は公開しない）。

### 2. OAuth UPSERT 側の更新

- `apps/api/app/services/sns_accounts.py` `upsert_sns_account` に `platform_account_id: str | None = None` パラメータを追加
- `apps/api/app/api/sns_accounts.py` の callback:
  - X: `oauth_x.exchange_code` が返す `user_id` を `platform_account_id` として渡す
  - IG: `oauth_ig.exchange_code` が返す `user_id`（ig_account_id）を `platform_account_id` として渡す

既存テスト（WEB-018）が壊れないよう、`platform_account_id` はデフォルト `None` で既定引数とする。WEB-020 で既に orchestrator が動いている場合、そちらに影響が出ないよう注意。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| 呼び出し方 | `get_publisher("ig")` → `IgPublisher.publish(...)` | WEB-020 の抽象に準拠 |
| 認証 | `sns_accounts.access_token` = IG長期アクセストークン（純粋な文字列、`:` 区切りなし） | WEB-018 IG OAuth の保存形式 |
| IG Business Account ID | `sns_accounts.platform_account_id` から取得 | 上記マイグレで追加 |
| 画像ホスト | `post_media.storage_path` が公開URL（R2）ならそのまま。R2環境変数が揃っていればPIL経由で再アップロードも可能にする | Phase 1 は「公開URL想定」を優先、R2 経由は option |
| HTTP | `requests` | 既存 `ig_auto_poster.py` と同じ |
| Graph API バージョン | `v19.0`（WEB-018 と揃える） | |
| エラー分類 | 4xx 認可・メディア拒否は即失敗、1-3 回の短いリトライはしない（Phase 1） | |
| ログ | access_token・app_secret・container_id/creation_id 以外は出さない | |
| テスト | `responses` でGraph API をモック | WEB-020 と同方針 |

---

## スコープ（WEB-021で実装するもの）

### 1. マイグレーション（前述）

`supabase/migrations/YYYYMMDDHHMMSS_sns_accounts_platform_id.sql` 新規。

### 2. `upsert_sns_account` 更新

`apps/api/app/services/sns_accounts.py` に `platform_account_id` を追加。既存シグネチャ互換を保つためデフォルト `None`。

### 3. コールバック更新

`apps/api/app/api/sns_accounts.py`:
- X callback: `platform_account_id=token_data["user_id"]`
- IG callback: `platform_account_id=token_data["user_id"]`

### 4. `ig_publisher.py` 仕様

`apps/api/app/services/publisher/ig_publisher.py` 新規:

- **コンストラクタ**: 設定不要（Consumer key 等は不使用、ユーザー固有トークンのみ）
- `publish(text, image_urls, account, options=None)`:
  - `account["access_token"]` を長期トークンとして直接使用
  - `account["platform_account_id"]` を IG Business Account ID として使用（なければエラー）
  - `image_urls` が 0 枚 → `PublishResult(success=False, error_message="IG requires at least one image")`
  - `len(image_urls) == 1`: 単一画像フロー
    - `POST {ig_id}/media`（body: `image_url`, `caption`, `access_token`）→ container_id
    - `POST {ig_id}/media_publish`（body: `creation_id`, `access_token`）→ ig_post_id
  - `2 <= len <= 10`: カルーセル フロー
    - 各 image_url に対し `POST {ig_id}/media`（`is_carousel_item=true`, `image_url`, `access_token`）→ child_ids
    - `POST {ig_id}/media`（`media_type=CAROUSEL`, `children=child_ids_comma`, `caption`, `access_token`）→ parent container
    - `POST {ig_id}/media_publish`（`creation_id=parent`）→ ig_post_id
  - `len > 10`: カルーセル最大10枚の制限を超過 → `PublishResult(success=False, error_message="IG carousel supports up to 10 images")`
  - Container 作成後、ステータスチェック（`GET /{container_id}?fields=status_code`）→ `FINISHED` になるまで最大5回ポーリング（1秒 sleep）
  - 成功時: `PublishResult(success=True, platform_post_id=ig_post_id)`
  - 失敗時: Graph API のエラーメッセージを extract
  - 例外（ネットワーク等）は全て握り潰して `PublishResult(success=False, error_message=...)`
- `options`:
  - `location_id`: 位置情報（Phase 1 では未サポート、受け取ってもスキップ）

### 5. R2 経由のオプション再アップロード（任意）

**Phase 1 は不採用**。`post_media.storage_path` が `http(s)://` で始まらない場合はエラーで失敗させるシンプル方式。

将来 (WEB-024) で Supabase Storage からの自動中継を実装する。

### 6. ファクトリ更新

`apps/api/app/services/publisher/__init__.py` の `get_publisher` に IG 分岐を追加:

```python
elif platform == "ig":
    return IgPublisher()
```

**WEB-020 が未マージの場合**でも、ファクトリは上記のシグネチャに準拠すること。WEB-020 での実装次第で微調整可能（例: キーワード引数の形 etc）。

### 7. orchestrator 影響確認

`apps/api/app/services/publisher/orchestrator.py` はプラットフォーム不可知にしておく。`publish_target` 内で `account` を渡すときに `platform_account_id` を必ず含めるよう修正:
- 現状 `sns_accounts` 本体から読んでいるはず → `select("*")` で `platform_account_id` も自動で入る
- IgPublisher が `account.get("platform_account_id")` を参照するので key 名を揃える

WEB-020 の orchestrator のコードが `account` dict に何を入れているかに合わせる。

### 8. テスト（`apps/api/tests/services/test_ig_publisher.py` 新規）

- 単一画像 成功: `/media` → container → status check (FINISHED) → `/media_publish` → ig_post_id 返却
- カルーセル 3枚 成功: 子3つ → 親 → publish
- 画像 0枚 → 失敗
- 画像 11枚 → 失敗
- Container IN_PROGRESS ポーリング後 FINISHED → 成功
- Container ERROR → 失敗
- Access token missing → 失敗
- platform_account_id missing → 失敗
- 4xx レスポンス → 失敗・error_message に status 含む

`test_publisher_orchestrator.py` にも IG 分岐テストを追加（既存 WEB-020 のテストケースを拡張）。

### 9. 既存テスト維持

WEB-018 のテスト (`test_sns_accounts.py`) は `platform_account_id` 追加後も通ること。既存 InMemoryAccountStore モック側で `platform_account_id` フィールドに対応させる（オプショナル扱い）。

### 10. 依存追加

- `requests` は WEB-020 で追加済想定（重複追加しない）
- `responses` 同様
- 追加依存なし（R2 を使わないため `boto3` は不要）

### 11. README 更新

`apps/api/README.md` の Publisher 節に IG を追記:
- IG Business Account ID の前提（`platform_account_id` 必須）
- 公開URL前提（`storage_path` = R2等の http(s)://）
- カルーセル 2-10 枚対応
- リポスト / リールは Phase 2

---

## スコープ外（やらないこと）

- ❌ R2 中継アップロード（Phase 2 / WEB-024）
- ❌ 動画 / リール投稿（Phase 2）
- ❌ Instagram Stories（Phase 2）
- ❌ Celery タスク結線（WEB-022）
- ❌ フロントエンド表示（WEB-027）
- ❌ トークン有効期限警告（follow-up）
- ❌ 複数 IG アカウント切替UI（Phase 2）
- ❌ rate limit 監視
- ❌ `notifier.py` 移植（WEB-023）

---

## 必須検証コマンド

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# マイグレーション後 pytest
cd apps/api && poetry install
poetry run pytest

# ruff
poetry run ruff check .

# フロント影響なし
cd ../.. && pnpm typecheck && pnpm build
```

`pytest` は WEB-018 既存 + WEB-020 追加 + WEB-021 追加の総和が全 passed であること。

---

## 絶対守るべきこと

- **CLAUDE.md Codex CLI Usage 節**: 偽装禁止
- **秘密情報をログ出力しない**（access_token, app_secret）
- **`app.core.supabase.get_supabase_client` 経由**のみ DB アクセス
- **既存 `ig_auto_poster.py` は触らない**（プロジェクト直下で稼働中）
- **既存 WEB-018 `sns_accounts_safe` ビューは変更しない**（`platform_account_id` は含めない）
- **`apps/web/` 変更禁止**
- **`apps/api/app/services/publisher/base.py` の Publisher 抽象契約は変えない**（WEB-020 準拠）
- **既存 pytest 全件維持**
- **本番 Supabase / 本番 Graph API に実呼び出ししない**。テストは全て mock
- **Finder 複製 / 偽装 shim / `* 2.*` 禁止**

---

## 成果物チェックリスト

- [ ] `supabase/migrations/YYYYMMDDHHMMSS_sns_accounts_platform_id.sql` 新規
- [ ] `apps/api/app/services/sns_accounts.py` に `platform_account_id` パラメータ追加
- [ ] `apps/api/app/api/sns_accounts.py` callback で `platform_account_id` を保存
- [ ] `apps/api/app/services/publisher/ig_publisher.py` 新規
- [ ] `apps/api/app/services/publisher/__init__.py` に IG 分岐追加
- [ ] `apps/api/tests/services/test_ig_publisher.py` 新規（9+ケース）
- [ ] `apps/api/tests/services/test_publisher_orchestrator.py` に IG 分岐テスト追加
- [ ] `apps/api/tests/api/test_sns_accounts.py` の既存テストが `platform_account_id` 対応後も全通過
- [ ] `apps/api/README.md` 更新
- [ ] `poetry run pytest` 全passed
- [ ] `poetry run ruff check .` 全通過
- [ ] `pnpm typecheck` 成功
- [ ] 偽装・Finder複製なし
- [ ] スコープ外の実装混入なし

---

## コミット指示

- `git add` は明示指定のみ
- `.env` はコミット対象外
- 生成物 `apps/web/src/generated/` は触らない
- コミットメッセージ: `feat: WEB-021 Instagram投稿Publisher実装 + platform_account_id`
- Co-Authored-By 不要（Claude 側で最終コミット時に付与）

---

## 補足: 関連設計ドキュメント / コード

- `design/design/IMPLEMENTATION_PLAN.md` L648 WEB-021 定義
- `design/design/PLATFORM_MATRIX.md` L41-43 IG 認証方式・エラー挙動
- `ig_auto_poster.py` L254-380 — 既存 IG 投稿ロジック
- `apps/api/app/services/oauth_ig.py` — WEB-018 で追加した IG OAuth
- `apps/api/app/services/publisher/base.py` (WEB-020) — Publisher 抽象契約
- `docs/codex_brief_WEB-020.md` — X Publisher ブリーフ（同じ設計方針）

---

## 補足: 環境情報

- Python 3.12+ / FastAPI 0.115+ / Supabase Python SDK v2
- Graph API v19.0
- 追加依存なし（WEB-020 で入れた requests / responses を再利用）

**Codex 側で実施**: コード実装、マイグレーション、pytest モック、ruff。
**Claude 側で実施**: `poetry install`, Supabase migration 適用、WEB-022 着手時の Celery 結線、実投稿検証。
