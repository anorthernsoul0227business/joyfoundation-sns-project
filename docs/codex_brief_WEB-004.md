# Codexブリーフィング: WEB-004 DBスキーマ作成（organizations/org_members/users）

**作成日**: 2026-04-18
**担当Issue**: WEB-004（Sprint 1 / 工数: 1日）
**依存**: WEB-003（コミット済 `fd8699d`）
**後続ブロック**: WEB-005（RLSポリシー適用）、WEB-006（認証API）

---

## タスク概要

マルチテナント基盤となる3テーブル（`organizations`、`org_members`、`users`）と、ユーザー登録時に自動で個人組織を作成するトリガーを Supabase Migration (純SQL) として作成する。Phase 2 のチーム機能を見据えた `org_id` カラムを今から仕込むことが本Issueの最大の価値。

**重要な設計判断**:
- IMPLEMENTATION_PLAN の「Alembic」は廃案。**Pure Supabase migrations (SQL) を採用**
- 理由: supabase-py は PostgREST 経由、auth.* との連携、RLS を純SQLで記述できる
- SQLAlchemy モデルは Phase 1 では導入しない（複雑クエリが必要になった時点で後付け）

---

## スコープ（WEB-004で実装するもの）

### 1. マイグレーションファイル作成

`sns-calendar-app/supabase/migrations/` 配下に以下のSQLファイルを作成:

**ファイル名**: `YYYYMMDDHHMMSS_initial_schema.sql`（タイムスタンプは作成時点、例: `20260418100000_initial_schema.sql`）

**含める内容**:

#### 1.1 `private` スキーマ作成
```sql
-- sensitive functions/triggers用の隠しスキーマ
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC;
GRANT USAGE ON SCHEMA private TO postgres, service_role;
```

#### 1.2 `public.organizations` テーブル
```sql
CREATE TABLE public.organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_user_id UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.organizations IS
  'マルチテナント組織。Phase 1ではユーザー作成時に個人organが自動生成される';
```

#### 1.3 `public.org_members` テーブル
```sql
CREATE TABLE public.org_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL DEFAULT 'member'
    CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (org_id, user_id)
);

COMMENT ON TABLE public.org_members IS
  '組織メンバーシップ。Phase 2チーム機能の土台';
```

#### 1.4 `public.users` プロファイルテーブル
```sql
CREATE TABLE public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  display_name TEXT,
  ui_mode VARCHAR(20) NOT NULL DEFAULT 'simple'
    CHECK (ui_mode IN ('simple', 'pro')),
  help_mode_enabled BOOLEAN NOT NULL DEFAULT true,  -- 決定事項#27
  default_org_id UUID REFERENCES public.organizations(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.users IS
  'auth.usersの公開プロファイル。UI設定・所属組織を保持';
```

**注意点**:
- `help_mode_enabled` は決定事項#27（ヘルプモードトグル）のため追加
- `ui_mode` は決定事項のシンプル/プロモード（pet APP_DESIGN_SPEC）

#### 1.5 パフォーマンスインデックス
RLS_DESIGN.md セクション8に準拠:
```sql
CREATE INDEX idx_org_members_user_id ON public.org_members (user_id);
CREATE INDEX idx_org_members_org_id ON public.org_members (org_id);
-- UNIQUE制約が既にインデックスを作るので org_members(org_id, user_id) は省略可

CREATE INDEX idx_users_default_org ON public.users (default_org_id);
CREATE INDEX idx_organizations_owner ON public.organizations (owner_user_id);
```

#### 1.6 `updated_at` 自動更新トリガー
```sql
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER organizations_set_updated_at
  BEFORE UPDATE ON public.organizations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER users_set_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

#### 1.7 `handle_new_user` 関数とトリガー
**RLS_DESIGN.md セクション 1.3 に準拠**（そのままコピー推奨）:

```sql
CREATE OR REPLACE FUNCTION private.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  new_org_id UUID;
  resolved_display_name TEXT;
BEGIN
  resolved_display_name := COALESCE(
    NEW.raw_user_meta_data->>'display_name',
    split_part(NEW.email, '@', 1)
  );

  -- 個人organization自動作成
  INSERT INTO public.organizations (name, owner_user_id)
  VALUES (resolved_display_name || '''s Workspace', NEW.id)
  RETURNING id INTO new_org_id;

  -- 自分をownerとして追加
  INSERT INTO public.org_members (org_id, user_id, role)
  VALUES (new_org_id, NEW.id, 'owner');

  -- profile作成
  INSERT INTO public.users (id, email, display_name, ui_mode, default_org_id, help_mode_enabled)
  VALUES (
    NEW.id,
    NEW.email,
    resolved_display_name,
    'simple',
    new_org_id,
    true
  );

  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION private.handle_new_user();
```

### 2. シード用サンプルデータ（任意だが推奨）

`sns-calendar-app/supabase/seed.sql` を作成（ローカル開発用、本番適用しない）:
```sql
-- 開発用サンプルデータ
-- Supabase ローカル環境で supabase db reset 時にのみ実行
-- 本番ではスキップされる
```
※中身は空でOK、ファイルだけ作成して WEB-006 以降で使用

### 3. ローカル検証手順の文書化

`sns-calendar-app/README.md` の「Supabase 設定」章に追記:
- `supabase db reset` でマイグレーション適用確認
- マイグレーション追加時のワークフロー
- リモートへの反映方法（`supabase db push`、本タスクでは実行しない）

### 4. マイグレーション検証テスト

`sns-calendar-app/apps/api/tests/test_schema.py` を新規作成:
- Supabase Service Role client で以下を検証:
  - `organizations` テーブル存在確認（`SELECT * FROM public.organizations LIMIT 0`）
  - `org_members` テーブル存在確認
  - `public.users` テーブル存在確認
  - テーブル間FKが適切に設定されているか（intentional error で検証）
- 既存の test_supabase.py と同様、環境変数未設定時は skip

---

## スコープ外（やらないこと）

- ❌ RLSポリシー定義（WEB-005）
- ❌ `get_user_org_ids()` ヘルパー関数（WEB-005でRLS時に追加）
- ❌ posts / sns_accounts / notifications 等の他テーブル（Sprint 2以降）
- ❌ SQLAlchemy モデル定義
- ❌ 認証API実装（WEB-006）
- ❌ リモートDB（本番Supabase）への `supabase db push` 実行
- ❌ フロントエンド側の型生成（WEB-002で整備済み、適宜再実行のみ）

---

## 必須検証コマンド

```bash
cd sns-calendar-app

# 1. マイグレーションファイル存在確認
test -f supabase/migrations/*_initial_schema.sql

# 2. ローカル Supabase 起動 → マイグレーション適用
#    (Docker必須、既に稼働中)
supabase start           # 初回は15分程度
supabase db reset        # マイグレーションを再適用

# 3. テーブル存在確認
supabase db dump --db-url "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
  --schema public -f /tmp/schema_dump.sql
grep -q "CREATE TABLE.*organizations" /tmp/schema_dump.sql
grep -q "CREATE TABLE.*org_members" /tmp/schema_dump.sql
grep -q "CREATE TABLE.*\.users " /tmp/schema_dump.sql

# 4. トリガー動作確認（auth.users にダミーINSERT → organizations/org_members/users が自動作成）
#    Supabase Studio (http://localhost:54323) で手動検証も可

# 5. Python側のテスト
cd apps/api && poetry run pytest

# 6. 既存 WEB-001/002/003 が維持されていること
cd ../.. && pnpm typecheck && pnpm build && pnpm lint

# 7. 終了
supabase stop
```

---

## 絶対守るべきこと

- **WEB-001/002/003 の成果物を壊さない**
- **`supabase db push` を本番リモートに実行しない**（ローカル検証のみ）
- **既存の `.env` 値を変更しない**（Service Role Keyは人間設定済み）
- スコープ外の実装禁止（他テーブル・RLS・認証API）
- axios は使わない（継続）
- **auth スキーマ（Supabase管理）には直接変更しない**（トリガー追加のみ）

---

## 成果物チェックリスト（レビュー項目）

- [ ] `supabase/migrations/YYYYMMDDHHMMSS_initial_schema.sql` が存在
- [ ] `organizations` / `org_members` / `public.users` テーブル作成SQL含む
- [ ] `help_mode_enabled` カラムが users テーブルにある（決定事項#27対応）
- [ ] `private` スキーマと `handle_new_user` 関数が含まれる
- [ ] `on_auth_user_created` トリガーが auth.users に設定される
- [ ] インデックス（org_members系、users系、organizations系）が定義されている
- [ ] `supabase db reset` で migration が正常適用
- [ ] トリガー動作確認（新規ユーザー登録 → 個人org + member + profile 自動作成）
- [ ] `tests/test_schema.py` で3テーブル存在確認テスト
- [ ] `poetry run pytest` 全パス
- [ ] `pnpm typecheck / build / lint` 維持
- [ ] `supabase/seed.sql` が存在（空でOK）
- [ ] README のSupabase章にマイグレーションワークフロー追記
- [ ] スコープ外の実装が混入していない

---

## コミット指示

- `git add` は明示指定のみ（`git add .` 禁止）
- `.env` は絶対コミットしない
- コミットメッセージ: `feat: WEB-004 初期DBスキーマ（organizations/org_members/users）`
- Co-Authored-By 不要

---

## 補足: 関連設計ドキュメント

- `design/design/RLS_DESIGN.md` セクション 1（テーブル構造）、8（インデックス戦略）
- `design/design/APP_DESIGN_SPEC.md` 決定事項 #11（org_id方式）、#27（ヘルプモード）
- `design/design/IMPLEMENTATION_PLAN.md` セクション 5.1（Sprint 1 詳細）

---

## 補足: Codex環境情報

- Supabase CLI: v2.90.0 @ `/opt/homebrew/bin/supabase`
- Docker: v28.5.2 稼働中
- poetry: v2.3.4 @ `~/.local/bin/poetry`
- pnpm: v9.15.9
- Python: 3.11.14
- `sns-calendar-app/.env` は人間側で設定済み（service_role key含む、コミット対象外）

**重要**: `supabase start` の初回実行はDockerイメージDLで15分程度かかる。既に起動済みの可能性もあるので `supabase status` で確認後、必要に応じて `supabase start`。
