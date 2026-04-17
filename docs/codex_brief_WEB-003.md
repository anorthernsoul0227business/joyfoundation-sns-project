# Codexブリーフィング: WEB-003 Supabase プロジェクト + ローカルCLI設定

**作成日**: 2026-04-17
**担当Issue**: WEB-003（Sprint 1 / 工数: 0.5日）
**依存**: WEB-001（コミット済 `ac03b27`）、WEB-002（コミット済 `759b23f`）
**後続ブロック**: WEB-004（DBスキーマ）以降のDB系Issue

---

## タスク概要

Supabase をローカル開発とリモート接続の両方で使えるように、**プロジェクト設定・環境変数・クライアント初期化コード・ドキュメント**を整備する。リモートプロジェクトは既に人間側で作成済みのため、その接続情報を組み込む。

---

## 既に完了している事前作業（人間側）

- ✅ Supabase アカウント作成済み
- ✅ Organization「SNS Calendar App」作成済み（Free plan）
- ✅ リモートプロジェクト `sns-calendar-app` 作成済み
  - **URL**: `https://msghvqclexpvgkrctxug.supabase.co`
  - **Project Ref**: `msghvqclexpvgkrctxug`
  - **Region**: Northeast Asia (Tokyo)
  - **Enable automatic RLS**: ✅ 有効
- ✅ Supabase CLI インストール済み（v2.90.0 via Homebrew）
- ✅ Database password は 1Password 等に保存済み（.env には手動入力予定）
- ✅ Publishable key: `sb_publishable_UIQSGZGY2Ds3LEDcQPhxNA_Af7tyFGB`
- ⚠️ Secret key は人間側で直接 `.env` に設定（このブリーフィングには含めない）

---

## スコープ（WEB-003で実装するもの）

### 1. Supabase ローカルプロジェクト初期化

- `sns-calendar-app/supabase/` ディレクトリ作成（`supabase init` を実行）
- **注意**: `supabase init` は対話的に確認を求めるが、`--force` と `--with-vscode-settings=false` 等の非対話フラグで回避
- 生成される `supabase/config.toml` はリポジトリコミット対象
- `supabase/migrations/` は空でOK（WEB-004以降で使用）

### 2. Python 側の Supabase クライアント追加

`apps/api/pyproject.toml` に依存追加:
```toml
supabase = "^2.7.0"  # 公式 supabase-py
```

`apps/api/app/core/supabase.py` 新規作成:
```python
"""Supabase client singleton for FastAPI.

Usage:
    from app.core.supabase import get_supabase_client
    client = get_supabase_client()
"""
from functools import lru_cache
from supabase import Client, create_client
from app.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return a service_role Supabase client for backend usage.

    RLSをバイパスして全テーブルにアクセス可能。
    認証されたユーザーとして動作する場合は別途 get_user_client() を使うこと。
    """
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def get_anon_client() -> Client:
    """Return a publishable (anon) key client.

    RLSポリシーが適用される。フロントエンドと同等の権限。
    テスト用途で使うケースが中心。
    """
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
```

### 3. 環境変数の config 追加

`apps/api/app/config.py` を更新:
- pydantic-settings で以下の環境変数を読み込み:
  - `SUPABASE_URL`: str
  - `SUPABASE_ANON_KEY`: str
  - `SUPABASE_SERVICE_ROLE_KEY`: SecretStr（pydantic.SecretStr 推奨）
- 既存の `app_name` 設定等は維持
- `.env` を自動読み込み（`model_config = SettingsConfigDict(env_file=".env", ...)` 等）

### 4. .env ファイル群の整備

`sns-calendar-app/.env.example` 新規作成:
```bash
# Supabase
SUPABASE_URL=https://msghvqclexpvgkrctxug.supabase.co
SUPABASE_ANON_KEY=sb_publishable_UIQSGZGY2Ds3LEDcQPhxNA_Af7tyFGB
SUPABASE_SERVICE_ROLE_KEY=__set_this_manually__  # Settings → API Keys → Secret keys → Reveal

# FastAPI
APP_NAME=sns-calendar-api
```

**重要**:
- `sns-calendar-app/.env` は作成しない（人間が手動でコピーして秘密キーを入れるため）
- `.gitignore` に `.env` が既に入っているか確認（既に入っている想定だが要確認）

### 5. FastAPI 側の接続テスト（最小）

`apps/api/tests/test_supabase.py` を新規作成:
- Supabaseクライアントが正常に初期化できることを確認するテスト（オフラインでもOK）
- `get_supabase_client()` が `Client` インスタンスを返すこと
- クライアントの `url` 属性が `SUPABASE_URL` 環境変数と一致すること
- **注意**: 実際にAPIを叩くテストは書かない（CI環境でのネットワーク依存を避けるため）
- 環境変数が未設定の場合はテストを skip する仕組み（`pytest.skip` or `pytest.mark.skipif`）

### 6. ローカル Supabase スタック動作確認

ブリーフィング実行時に以下を試す（Docker必須、既に稼働中）:
```bash
cd sns-calendar-app
supabase start
```
- 初回起動は依存イメージのダウンロードで時間がかかる（5-15分）
- 成功すれば API URL、anon key、service_role key、Studio URL が表示される
- 終了確認: `supabase stop`

**備考**: サンドボックスの制約で `supabase start` が動かない場合は、コマンドとドキュメントだけ整備して「手動実行で検証済み」と報告可。

### 7. README 更新

`sns-calendar-app/README.md` に「Supabase 設定」章を追加:

````markdown
## Supabase 設定

### 初回セットアップ

1. 依存をインストール
   ```bash
   cd apps/api && poetry install  # supabase-py を含む
   ```

2. 環境変数を設定
   ```bash
   cp .env.example .env
   # .env を開いて SUPABASE_SERVICE_ROLE_KEY に値を設定
   # （Supabase Dashboard → Settings → API Keys → Secret keys → Reveal）
   ```

3. ローカルで Supabase を起動（開発用）
   ```bash
   supabase start  # 初回は5-15分かかる
   ```

4. ローカルの管理UIにアクセス
   ```
   Studio: http://localhost:54323
   ```

### リモート接続の切替
`.env` の `SUPABASE_URL` と キー類を本番/ステージングのものに書き換える。

### マイグレーション
WEB-004 以降で `supabase/migrations/` 配下にSQL追加予定。
````

---

## やらないこと（スコープ外）

- ❌ 実際のDBスキーマ作成（WEB-004）
- ❌ Alembicマイグレーション（WEB-004）
- ❌ RLSポリシー（WEB-005）
- ❌ 認証API実装（WEB-006）
- ❌ フロントエンド側の @supabase/supabase-js 導入（Sprint 2以降）
- ❌ `.env` 実ファイルの作成（人間が手動）
- ❌ 本番 DB への接続テスト

---

## 必須検証コマンド

```bash
cd sns-calendar-app

# 1. supabase CLI 初期化成功
test -f supabase/config.toml
test -d supabase/migrations

# 2. Python側
cd apps/api && poetry install
poetry run python -c "from app.core.supabase import get_supabase_client; print('OK')"

# 3. テスト
poetry run pytest  # 新規テストを含めて全パス

# 4. 既存の WEB-001/002 成果物が壊れていないこと
cd ../.. && pnpm typecheck && pnpm build && pnpm lint

# 5. .env.example 存在確認
test -f .env.example
grep -q "SUPABASE_URL" .env.example
grep -q "SUPABASE_SERVICE_ROLE_KEY" .env.example
```

---

## 絶対守るべきこと

- **WEB-001/WEB-002 の成果物を壊さない**（typecheck/build/lint/pytest が維持される）
- **Secret key (service_role key) をコードやコミットに絶対含めない**
- `.env` は作成しない（`.env.example` のみ）
- スコープ外の実装禁止
- axios は使わない（継続）
- **supabase-py のバージョンは `^2.7.0` 以上**（それ以前のバージョンは API異なる）

---

## 成果物チェックリスト（レビュー項目）

- [ ] `sns-calendar-app/supabase/config.toml` が存在
- [ ] `sns-calendar-app/supabase/migrations/` ディレクトリが存在（空でOK）
- [ ] `apps/api/app/core/supabase.py` に `get_supabase_client()` / `get_anon_client()` 実装
- [ ] `apps/api/app/config.py` に 3つの Supabase 環境変数 追加
- [ ] `apps/api/pyproject.toml` に `supabase = "^2.7.0"` 追加
- [ ] `apps/api/tests/test_supabase.py` が存在し、pytest 全パス
- [ ] `sns-calendar-app/.env.example` が存在
- [ ] `.gitignore` に `.env` が含まれる（既存確認）
- [ ] README に Supabase 設定章が追加
- [ ] 既存の `pnpm typecheck / build / lint` および `poetry run pytest` が通る
- [ ] スコープ外の実装が混入していない
- [ ] コミット内容に秘密キー類が含まれていない

---

## コミット指示

- `git add` は明示指定（`git add .` 禁止）
- `.env`（実ファイル）は絶対コミット対象に含めない
- コミットメッセージ: `feat: WEB-003 Supabase クライアント設定`
- Co-Authored-By 不要

---

## 補足: 関連設計ドキュメント

- `design/design/RLS_DESIGN.md` — RLS全体設計（WEB-005で参照、今回は読むだけ）
- `design/design/APP_DESIGN_SPEC.md` 決定事項#2, #12-14（Supabase方針）
- `design/design/IMPLEMENTATION_PLAN.md` セクション3（インフラ構成）
- `docs/codex_brief_WEB-001.md` / `docs/codex_brief_WEB-002.md` — 前段ブリーフィング（コンテキスト用）
