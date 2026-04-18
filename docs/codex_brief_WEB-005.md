# Codexブリーフィング: WEB-005 RLSポリシー適用

**作成日**: 2026-04-18
**担当Issue**: WEB-005（Sprint 1 / 工数: 1日）
**依存**: WEB-004（コミット済 `a21735e`）
**後続ブロック**: WEB-006（認証API）以降、全ての認証済みアクセス

---

## タスク概要

WEB-004 で作成した3テーブル（`organizations` / `org_members` / `public.users`）に **RLS（Row Level Security）ポリシー** を適用する。Supabase 採用プロジェクトにおける**最重要セキュリティ境界**のため、ヘルパー関数・ポリシー・テストの3点セットを確実に実装する。

**背景**: Supabase セキュリティ事故の 83% は RLS 漏れ。ポリシー未定義の場合、RLS 有効でもテーブルは「service_role のみアクセス可、一般ユーザーは全アクセス不可」状態。WEB-004 完了時点で `auth.users` トリガー経由以外のアクセスができない状態にある。

---

## スコープ（WEB-005で実装するもの）

### 1. マイグレーションファイル作成

`sns-calendar-app/supabase/migrations/YYYYMMDDHHMMSS_rls_policies.sql` 新規作成（新しいタイムスタンプで）

#### 1.1 ヘルパー関数（RLS_DESIGN.md セクション 2.1 準拠）

```sql
-- ユーザーが所属するorg_idの一覧を返す（最頻出）
CREATE OR REPLACE FUNCTION public.get_user_org_ids()
RETURNS SETOF UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT org_id
  FROM public.org_members
  WHERE user_id = (SELECT auth.uid());
$$;

-- 特定orgでの権限チェック
CREATE OR REPLACE FUNCTION public.has_org_role(
  p_org_id UUID,
  p_role VARCHAR DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.org_members
    WHERE user_id = (SELECT auth.uid())
      AND org_id = p_org_id
      AND (p_role IS NULL OR role = p_role)
  );
$$;

-- 編集権限チェック（owner, admin, editor）
CREATE OR REPLACE FUNCTION public.can_edit_org(p_org_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.org_members
    WHERE user_id = (SELECT auth.uid())
      AND org_id = p_org_id
      AND role IN ('owner', 'admin', 'editor')
  );
$$;
```

#### 1.2 `public.organizations` RLSポリシー（RLS_DESIGN.md 2.2 準拠）

```sql
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_select" ON public.organizations
  FOR SELECT TO authenticated
  USING (id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "org_update" ON public.organizations
  FOR UPDATE TO authenticated
  USING (public.has_org_role(id, 'owner') OR public.has_org_role(id, 'admin'))
  WITH CHECK (public.has_org_role(id, 'owner') OR public.has_org_role(id, 'admin'));

CREATE POLICY "org_insert" ON public.organizations
  FOR INSERT TO authenticated
  WITH CHECK ((SELECT auth.uid()) = owner_user_id);

CREATE POLICY "org_delete" ON public.organizations
  FOR DELETE TO authenticated
  USING ((SELECT auth.uid()) = owner_user_id);
```

#### 1.3 `public.org_members` RLSポリシー（RLS_DESIGN.md 2.3 準拠）

```sql
ALTER TABLE public.org_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "members_select" ON public.org_members
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "members_insert" ON public.org_members
  FOR INSERT TO authenticated
  WITH CHECK (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'));

CREATE POLICY "members_update" ON public.org_members
  FOR UPDATE TO authenticated
  USING (
    (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'))
    AND NOT (user_id = (SELECT auth.uid()) AND role = 'owner')
  );

CREATE POLICY "members_delete" ON public.org_members
  FOR DELETE TO authenticated
  USING (
    (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'))
    AND NOT (user_id = (SELECT auth.uid()) AND role = 'owner')
  );
```

#### 1.4 `public.users` RLSポリシー（本ブリーフィングで新規設計）

RLS_DESIGN.md には未記載のため、以下の方針で実装:
- **SELECT**: 自分のプロファイル + 同じorg所属メンバーのプロファイル
- **UPDATE**: 自分のプロファイルのみ（ui_mode / display_name / help_mode_enabled 変更を想定）
- **INSERT/DELETE**: ユーザー操作不可（auth.users トリガー経由のみ、service_role が担当）

```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profile_select_self" ON public.users
  FOR SELECT TO authenticated
  USING (
    id = (SELECT auth.uid())
    OR id IN (
      SELECT user_id
      FROM public.org_members
      WHERE org_id IN (SELECT public.get_user_org_ids())
    )
  );

CREATE POLICY "profile_update_self" ON public.users
  FOR UPDATE TO authenticated
  USING (id = (SELECT auth.uid()))
  WITH CHECK (id = (SELECT auth.uid()));

-- INSERT/DELETE policy は明示的に「authenticated からは不可」
-- (policy未定義 = 一般ユーザーは操作不可、service_role のみ)
```

### 2. RLSポリシー検証テスト

`sns-calendar-app/apps/api/tests/test_rls.py` 新規作成:

テストケース（全てローカル Supabase のみ実行、環境判定は test_schema.py と同様）:

1. **setUp**: 2人のテストユーザーを作成（異なる個人org）
2. **anonクライアント**は authenticated 扱いできないため、各ユーザーの JWT を発行して個別クライアントを作る
3. **検証項目**:
   - ✅ ユーザーAはA自身のprofileを SELECT できる
   - ✅ ユーザーAはA自身のorganizationを SELECT できる
   - ❌ ユーザーAはユーザーBのorganizationを SELECT **できない**（所属していない）
   - ❌ ユーザーAはユーザーBのprofileを SELECT **できない**（別org）
   - ❌ ユーザーAはユーザーBのorganizationを UPDATE **できない**
   - ✅ ユーザーAは自分のprofileを UPDATE できる（help_mode_enabled 変更等）
   - ✅ service_role クライアントは両方のuserを SELECT できる（RLSバイパス確認）

JWT 発行方法:
```python
# service_role client で auth.admin.generate_link() か
# client.auth.sign_in_with_password() でセッション取得
# セッションから access_token を取得して新規 Client に与える
```

あるいは、シンプルに `client.auth.sign_in_with_password()` でユーザーログインし、その `client.postgrest.auth(access_token)` を使う。

### 3. ドキュメント更新

`sns-calendar-app/README.md` に追記:
- RLS の動作確認手順（Supabase Studio で Policies 表示）
- トラブルシューティング: service_role を誤って使わない注意

### 4. RLS_DESIGN.md との差分記録

設計書と実装の差分を `sns-calendar-app/supabase/migrations/README.md` に記録（新規作成）:
- `public.users` のポリシーは本タスクで新規設計した旨
- 今後の他テーブル（posts等）のポリシーは Sprint 2-3 で追加予定

---

## スコープ外（やらないこと）

- ❌ posts / sns_accounts / notifications 等の他テーブル RLS（Sprint 2-3）
- ❌ 認証API実装（WEB-006）
- ❌ フロントエンドからの RLS 動作確認（WEB-007）
- ❌ 本番リモート DB への `supabase db push`（ローカル検証のみ）
- ❌ 既存マイグレーションの変更（新規 migration として追加）

---

## 必須検証コマンド

```bash
cd sns-calendar-app

# 1. 新規マイグレーション確認
ls supabase/migrations/*rls_policies*.sql

# 2. マイグレーション再適用
supabase db reset

# 3. ポリシー適用確認（Studio or psql 経由）
docker exec supabase_db_sns-calendar-app psql -U postgres -d postgres \
  -c "SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname='public' ORDER BY tablename, policyname;"
# → 少なくとも10件以上のポリシーが表示される想定

# 4. ヘルパー関数確認
docker exec supabase_db_sns-calendar-app psql -U postgres -d postgres \
  -c "\df public.get_user_org_ids public.has_org_role public.can_edit_org"
# → 3つの関数が STABLE / SECURITY DEFINER で表示

# 5. RLS テスト実行（ローカル環境変数で）
cd apps/api
SUPABASE_URL=http://127.0.0.1:54321 \
SUPABASE_ANON_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH \
SUPABASE_SERVICE_ROLE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz \
poetry run pytest -v

# 6. 既存の WEB-001〜004 が維持されていること
cd ../.. && pnpm typecheck && pnpm build && pnpm lint
```

**ローカル Supabase の認証キー**（検証用、コミット対象外）:
- URL: `http://127.0.0.1:54321`
- Anon: `sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH`
- Service role: `sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz`

---

## 絶対守るべきこと

- **WEB-001〜004 の成果物を壊さない**
- **本番リモート (msghvqclexpvgkrctxug.supabase.co) への push 禁止**
- **既存の `20260418100000_initial_schema.sql` は変更しない**（新規 migration として追加）
- スコープ外の実装禁止（他テーブル RLS・認証API・フロント）
- axios は使わない（継続）
- auth スキーマに直接変更を加えない（トリガーも追加しない、既存のみ）
- ポリシー名は `"<table>_<operation>"` または RLS_DESIGN.md 準拠の命名規則に従う
- **`(SELECT auth.uid())` の SELECT ラップ必須**（パフォーマンス最適化、RLS_DESIGN.md 決定事項#12）

---

## 成果物チェックリスト（レビュー項目）

- [ ] `supabase/migrations/*_rls_policies.sql` 新規作成
- [ ] 3つのヘルパー関数（get_user_org_ids / has_org_role / can_edit_org）定義
- [ ] `organizations` に 4 policy（select/insert/update/delete）
- [ ] `org_members` に 4 policy
- [ ] `public.users` に 2 policy（select/update のみ、insert/deleteは policy 定義せず）
- [ ] 全関数が `STABLE` + `SECURITY DEFINER` + `SET search_path = ''`
- [ ] 全 `auth.uid()` が `(SELECT auth.uid())` でラップされている
- [ ] `supabase db reset` 成功
- [ ] `pg_policies` にポリシーが10件以上登録
- [ ] `test_rls.py` 追加、テスト全パス
- [ ] 既存 `pnpm typecheck / build / lint / pytest (WEB-001〜004)` が維持
- [ ] README に RLS 確認手順追記
- [ ] `supabase/migrations/README.md` 新規作成（設計書差分記録）
- [ ] スコープ外の実装混入なし
- [ ] 本番リモートへの push なし

---

## コミット指示

- `git add` は明示指定のみ（`git add .` 禁止）
- `.env` は絶対コミットしない
- コミットメッセージ: `feat: WEB-005 RLSポリシー適用（organizations/org_members/users）`
- Co-Authored-By 不要

---

## 補足: 関連設計ドキュメント

- `design/design/RLS_DESIGN.md` セクション 2（テーブルポリシー）、8（インデックス戦略）、10-11（テスト）
- `design/design/APP_DESIGN_SPEC.md` 決定事項 #12（RLSポリシー）、#14（トークン保護）

---

## 補足: Codex環境情報

- Supabase CLI 2.90.0 @ `/opt/homebrew/bin/supabase`
- ローカル Supabase 起動中（`supabase status` で確認可）
- Docker 28.5.2 稼働中
- poetry 2.3.4 @ `~/.local/bin/poetry`（依存追加不要の想定、既存テストライブラリで実装可能）
- pnpm 9.15.9
- Python 3.11.14

**注意**: WEB-004 時点で `supabase start` 実行済み。`supabase status` で running 確認できる想定。未起動の場合のみ `supabase start` 実行。

作業後は `supabase stop` **しない**（次の Issue でも使うため、Docker起動しっぱなしでOK）。
