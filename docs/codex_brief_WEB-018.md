# Codexブリーフィング: WEB-018 SNSアカウント連携API（OAuth: X, IG）

**作成日**: 2026-04-21
**担当Issue**: WEB-018（Sprint 3 / 工数: 2日）
**依存**: WEB-010（posts/post_targets/post_media/sns_accounts DBスキーマ）
**Sprint 3 最初の Issue**

---

## タスク概要

X (Twitter) と Instagram のアカウントを OAuth 経由で接続・管理する API を `apps/api` に実装する。ユーザーが「接続」ボタンを押すと認可 URL が返り、プロバイダーの認可画面 → コールバックで access_token を受け取り `sns_accounts` に保存する流れを完成させる。

後続 Issue:
- WEB-019: 設定画面（このAPIを叩くフロント）
- WEB-020: X Publisher（このAPIで保存したトークンで実投稿）
- WEB-021: IG Publisher（同上）

---

## スコープ（WEB-018で実装するもの）

### 1. プラットフォーム範囲（Phase 1）

- ✅ **X**: OAuth 1.0a（User Context）— `X_CONSUMER_KEY` / `X_CONSUMER_SECRET` をアプリ側 credential として使用
- ✅ **Instagram**: OAuth 2.0 (Meta Graph API) — `META_APP_ID` / `META_APP_SECRET`、短期→長期トークン交換、`instagram_basic` + `instagram_content_publish` + `pages_show_list` + `pages_read_engagement` スコープ
- ❌ note / YouTube / LINE: Phase 2以降（スキップ）

### 2. 新規マイグレーション: `oauth_states` テーブル

CSRF対策の `state` を一時保管する小テーブルを追加:

```sql
-- supabase/migrations/YYYYMMDDHHMMSS_oauth_states.sql
CREATE TABLE public.oauth_states (
  state TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  platform VARCHAR(20) NOT NULL CHECK (platform IN ('x', 'ig')),
  -- X OAuth1.0a は request_token 交換が必要なので request_token 情報を保持
  request_token TEXT,
  request_token_secret TEXT,
  redirect_uri TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '10 minutes'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_oauth_states_expires ON public.oauth_states (expires_at);

-- RLS: service_role のみアクセス可能（フロント完全遮断）
ALTER TABLE public.oauth_states ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.oauth_states FROM authenticated, anon;
GRANT ALL ON public.oauth_states TO service_role;

COMMENT ON TABLE public.oauth_states IS
  'OAuth コールバック時の CSRF 検証用一時ステート。10分で失効、callback 消費で DELETE';
```

期限切れ行のクリーンアップは Phase 1 では簡易的に:
- callback 内で `DELETE FROM oauth_states WHERE expires_at < now()` を都度実行
- または後続 Sprint で Celery Beat ジョブ化

### 3. 新規エンドポイント（`apps/api/app/api/sns_accounts.py`）

| メソッド | パス | 認証 | 動作 |
|---|---|---|---|
| POST | `/api/sns-accounts/connect/{platform}` | JWT | 認可URL生成、state保存 → `{ authorization_url }` 返却 |
| GET | `/api/sns-accounts/callback/{platform}` | （state検証） | トークン取得 → `sns_accounts` UPSERT → 設定画面へ 302 |
| GET | `/api/sns-accounts` | JWT | `sns_accounts_safe` 経由で org_id 所属の一覧返却 |
| DELETE | `/api/sns-accounts/{id}` | JWT | `is_active = false` に更新（論理削除）|

`main.py` にルーター登録。`platform` は `x` / `ig` のみ受理、他は 400。

### 4. スキーマ（`apps/api/app/schemas/sns_account.py` 新規）

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, HttpUrl

Platform = Literal["x", "ig"]

class ConnectResponse(BaseModel):
    authorization_url: HttpUrl
    state: str

class SnsAccountSafe(BaseModel):
    id: UUID
    org_id: UUID
    platform: Platform
    handle: str
    display_name: str | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class SnsAccountListResponse(BaseModel):
    accounts: list[SnsAccountSafe]
```

### 5. サービス層（`apps/api/app/services/` 新規）

```
apps/api/app/services/
├── __init__.py
├── oauth_x.py         # X OAuth 1.0a 実装
├── oauth_ig.py        # Instagram OAuth 2.0 実装
└── sns_accounts.py    # sns_accounts UPSERT / 一覧 / 削除
```

#### `oauth_x.py`
- `build_authorization_url(callback_url: str) -> (authorization_url, request_token, request_token_secret)`
  - `requests-oauthlib` の `OAuth1Session` を使って `https://api.x.com/oauth/request_token` を叩く
  - `https://api.x.com/oauth/authorize?oauth_token=...` を組み立てて返す
- `exchange_code(oauth_token: str, oauth_verifier: str, request_token_secret: str) -> { access_token, access_token_secret, screen_name, user_id }`
  - `https://api.x.com/oauth/access_token` で本トークンを受け取る
- X は OAuth 1.0a のため `refresh_token` / `expires_at` は NULL 保存、`access_token` に `{oauth_token}:{oauth_token_secret}` 形式で保存（区切り文字注意、後で `split` 可）

#### `oauth_ig.py`
- `build_authorization_url(state: str, redirect_uri: str) -> authorization_url`
  - `https://www.facebook.com/v19.0/dialog/oauth?client_id=...&redirect_uri=...&state=...&scope=instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement`
- `exchange_code(code: str, redirect_uri: str) -> { access_token, user_id, pages, ig_business_account }`
  1. `GET /v19.0/oauth/access_token?...&code={code}` で短期トークン取得
  2. `GET /v19.0/oauth/access_token?grant_type=fb_exchange_token&...` で長期トークンに交換（約60日）
  3. `GET /v19.0/me/accounts` で紐づく Facebook Page 一覧
  4. `GET /v19.0/{page_id}?fields=instagram_business_account` で IG Business Account ID を解決
  5. `GET /v19.0/{ig_id}?fields=username` で `handle` 取得
- 複数ページ接続時は Phase 1 では**先頭1件のみ**保存（ログに警告、後続で選択UI）

### 6. 設定拡張（`apps/api/app/config.py`）

既存 `Settings` に以下を追加（すべて `Optional[str]`、未設定時は 500 で明示エラー）:

```python
x_consumer_key: str | None = None
x_consumer_secret: str | None = None
meta_app_id: str | None = None
meta_app_secret: str | None = None
oauth_redirect_base: str | None = None  # 例: "http://localhost:8000" or prod URL
```

`.env.example` に:
```
# OAuth プロバイダー認証情報
X_CONSUMER_KEY=
X_CONSUMER_SECRET=
META_APP_ID=
META_APP_SECRET=
OAUTH_REDIRECT_BASE=http://localhost:8000
```

ルートの `.env` には同名キーが既にあるので、`apps/api/.env` に同内容をコピーして使う運用を README に明記。

### 7. コールバック後のリダイレクト

成功時: `{OAUTH_REDIRECT_BASE}/settings/sns?connected={platform}&handle={handle}` に 302。
失敗時: `{OAUTH_REDIRECT_BASE}/settings/sns?error={reason}` に 302。

（`/settings/sns` ページは WEB-019 で作るので、現時点で存在しなくて良い。URLは合意しておく）

### 8. トークン保存

- `sns_accounts` の既存カラム構造で保存:
  - `access_token`: 上記形式の文字列
  - `refresh_token`: IG 長期トークンの場合は NULL（長期トークンが access_token として機能。リフレッシュは `/refresh_access_token` エンドポイントで別途実施、Phase 1 では未実装）
  - `expires_at`: IG の長期トークン期限（約60日後）
- **at-rest 暗号化は本 Issue 対象外**。RLS + service_role ゲートで保護。pgcrypto 導入は follow-up issue に記載:
  - `docs/` 配下に `codex_brief_WEB-018-FOLLOWUP.md` は作らなくてよい。DEVLOG の課題欄に追記のみ。

### 9. UPSERT 仕様

`UNIQUE (org_id, platform, handle)` 制約があるので:
- 同じ platform + handle の再接続 → `ON CONFLICT` で access_token/refresh_token/expires_at を更新、`is_active=true` に戻す
- 他 handle の追加接続 → 新規 INSERT

### 10. DELETE 動作

- 物理削除ではなく `UPDATE sns_accounts SET is_active = false` （`sns_accounts_safe` ビューは `is_active=true` のみ返す前提に合わせる）
- サービスは `service_role` の Supabase クライアントを使用（`core/supabase.py` の既存 getter）

### 11. ルーティング登録

`apps/api/app/main.py` に:
```python
from app.api import sns_accounts
app.include_router(sns_accounts.router, prefix="/api/sns-accounts", tags=["sns-accounts"])
```

### 12. OpenAPI 更新

```bash
cd apps/api && poetry run python scripts/export_openapi.py  # 既存スクリプトがあれば
cd ../.. && pnpm --filter @sns/shared-types generate
```

既存パイプラインに従う。新しい型が `packages/shared-types` に生成されることを確認。

### 13. テスト（`apps/api/tests/api/test_sns_accounts.py` 新規）

以下を pytest で:
- `POST /connect/x` / `POST /connect/ig` が authorization_url を返す（外部HTTPは `httpx.MockTransport` or `responses` でモック）
- `GET /callback/x` state 不一致で 400
- `GET /callback/ig` 正常系で sns_accounts に INSERT され 302 される
- `GET /sns-accounts` が自 org のみ返す（他 org の行は見えない）
- `DELETE /sns-accounts/{id}` で `is_active=false`、一覧から消える
- 未認証アクセスが 401

既存 pytest 件数（51件）を下回らないこと。

### 14. 手動検証（Claude 側で実施）

Codex では実 OAuth は実行不可。Codex には**モック単体テスト + 疎通のための curl 例**のみ依頼。Claude が別途 localhost で:
- X OAuth フローを完走
- IG OAuth フローを完走
- `sns_accounts` テーブルに行が入ることを確認

### 15. README 更新

`apps/api/README.md` に:
- OAuth 環境変数の設定手順
- `/api/sns-accounts/*` エンドポイント一覧
- ローカル開発時のコールバックURL設定例

---

## スコープ外（やらないこと）

- ❌ note / YouTube / LINE の OAuth 実装
- ❌ フロントエンド `/settings/sns` 画面（WEB-019）
- ❌ Publisher での投稿実行（WEB-020/021）
- ❌ トークンの at-rest 暗号化（pgcrypto）
- ❌ IG 長期トークンの自動リフレッシュ（60日期限直前の延長ジョブ）
- ❌ 複数 Facebook Page からの IG Business Account 選択UI
- ❌ `post_targets` への `sns_account_id` FK 追加（現行 `platform` 列でPublisher側が解決）
- ❌ `apps/web/src/generated/` の手動編集（生成物）

---

## 絶対守るべきこと

- **CLAUDE.md の Codex CLI Usage 節に従う**: 偽装絶対禁止。外部ライブラリは `poetry add` で正規インストール。
- **`requests-oauthlib`** は既に root 側で使用実績あり。`apps/api/pyproject.toml` に追加。
- **axios 不使用**（フロントのみの話だが念のため）
- **サービスロール Supabase クライアントは `core/supabase.py` 経由**。新規 import/初期化は不可。
- **既存テスト維持**（pytest 51件、pnpm 全タスク）
- **シークレットは `.env` のみ**。コミット対象外。`.env.example` の値は空文字で登録。
- **秘密情報をログ出力しない**（access_token / consumer_secret / ユーザーの request_token_secret 等）
- **Finder 複製 `* 2.*` を作らない**
- **マイグレーションファイル名は `YYYYMMDDHHMMSS_oauth_states.sql` 形式**（既存マイグレの命名に合わせる）

---

## 成果物チェックリスト

- [ ] `supabase/migrations/YYYYMMDDHHMMSS_oauth_states.sql` 新規（RLS含む）
- [ ] `apps/api/app/api/sns_accounts.py` 新規（4エンドポイント）
- [ ] `apps/api/app/schemas/sns_account.py` 新規
- [ ] `apps/api/app/services/oauth_x.py` 新規
- [ ] `apps/api/app/services/oauth_ig.py` 新規
- [ ] `apps/api/app/services/sns_accounts.py` 新規（UPSERT/list/soft-delete）
- [ ] `apps/api/app/config.py` 設定追加
- [ ] `apps/api/app/main.py` ルーター登録
- [ ] `apps/api/.env.example` 追加
- [ ] `apps/api/pyproject.toml` に `requests-oauthlib` 追加（既存なら不要）
- [ ] `apps/api/tests/api/test_sns_accounts.py` 新規（外部HTTPモック）
- [ ] `apps/api/README.md` 更新
- [ ] `packages/shared-types` 再生成、差分コミット
- [ ] `poetry run pytest` 既存+新規全通過
- [ ] `pnpm typecheck / build / lint` 通過
- [ ] 偽装 / shim / Finder複製 一切なし

---

## コミット指示

- `git add` は明示指定のみ
- `.env` / 実シークレット / `apps/api/.venv` / 生成キャッシュはコミット対象外
- コミットメッセージ: `feat: WEB-018 SNSアカウント連携API（X OAuth1.0a + IG OAuth2.0）`
- Co-Authored-By 不要

---

## 補足: 関連設計ドキュメント

- `design/design/APP_DESIGN_SPEC.md` L84 F-10、L369-379 SnsAccount スキーマ、L490-494 エンドポイント、L773 トークン保護
- `design/design/PLATFORM_MATRIX.md` L41-43 認証方式・有効期限、L112-127 X/IG エラー
- `design/design/RLS_DESIGN.md` L247-292 sns_accounts RLS、L443-463 sns_accounts_safe ビュー
- `supabase/migrations/20260420010431_posts_schema.sql` L83-125 既存テーブル定義
- `x_auto_poster.py` L24, L71-77 既存 X OAuth 実装（credential名の参考）
- `ig_auto_poster.py` L68-73 既存 IG 認証（META_APP_ID / IG_BUSINESS_ACCOUNT_ID の使い方）

---

## 環境情報

- FastAPI 0.115+ / Python 3.12 / Supabase Python SDK v2
- Next.js 15 + React 19（フロントは WEB-019 で着手）
- pnpm 9.15.9 / Node 25.2.1 / Poetry 1.8+
- `requests-oauthlib` は X OAuth1.0a 実装で root 側で実績あり

**重要**: 完了報告時に偽装スキャンの自己確認を実施してください。外部 API 疎通は Claude 側で実機検証します。
