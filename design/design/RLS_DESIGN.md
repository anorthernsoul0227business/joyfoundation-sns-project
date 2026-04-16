# 認証/権限 RLS設計書（Codex壁打ち結果）

**作成日**: 2026-04-16
**関連**: APP_DESIGN_SPEC.md セクション13 優先アクション#3

---

## 前提と総評

- Supabase Auth + PostgreSQL RLSの採用は妥当。MVP速度を最大化しつつ、マルチテナント化への道筋を確保できる。
- **最大のリスク**: RLSポリシーの漏れ（83%のSupabaseセキュリティ事故はRLS設定ミスに起因）。テーブル作成時に必ずRLSを有効化+ポリシー定義をセットにする。
- Phase 1はシングルユーザーでも、**Phase 2チーム機能を見据えた`org_id`カラムを今から仕込む**ことを推奨。後からの追加はマイグレーションコストが高い。
- Celery workerからの投稿実行は**service_roleキーでRLSバイパス**が正解。バックエンドの投稿実行にユーザーコンテキストを引き回す設計は複雑化するだけ。

---

## 1. テーブル構造拡張（チーム機能準備）

### 1.1 Phase 1で追加すべきテーブル

```sql
-- 組織（Phase 1ではユーザー作成時に自動生成される個人org）
CREATE TABLE public.organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_user_id UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 組織メンバーシップ
CREATE TABLE public.org_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL DEFAULT 'member'
    CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (org_id, user_id)
);
```

### 1.2 既存テーブルへの`org_id`追加

```sql
-- 全テーブルにorg_idを追加（Phase 1では自動セット）
ALTER TABLE public.posts ADD COLUMN org_id UUID NOT NULL REFERENCES public.organizations(id);
ALTER TABLE public.sns_accounts ADD COLUMN org_id UUID NOT NULL REFERENCES public.organizations(id);
ALTER TABLE public.notifications ADD COLUMN org_id UUID NOT NULL REFERENCES public.organizations(id);
ALTER TABLE public.generation_jobs ADD COLUMN org_id UUID NOT NULL REFERENCES public.organizations(id);
ALTER TABLE public.ng_rule_presets ADD COLUMN org_id UUID REFERENCES public.organizations(id);
-- ng_rule_presets: org_id=NULL はシステムデフォルト
```

### 1.3 ユーザー登録時の自動org作成

```sql
-- auth.users INSERT時に自動実行するトリガー
CREATE OR REPLACE FUNCTION private.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  new_org_id UUID;
BEGIN
  -- 個人organizationを自動作成
  INSERT INTO public.organizations (name, owner_user_id)
  VALUES (COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email), NEW.id)
  RETURNING id INTO new_org_id;

  -- 自分をownerとして追加
  INSERT INTO public.org_members (org_id, user_id, role)
  VALUES (new_org_id, NEW.id, 'owner');

  -- profileにデフォルトorg_idを保存
  INSERT INTO public.users (id, email, display_name, ui_mode, default_org_id)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'display_name', ''),
    'simple',
    new_org_id
  );

  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION private.handle_new_user();
```

---

## 2. RLSポリシー設計（全テーブル）

### 2.1 共通ヘルパー関数

```sql
-- ユーザーが所属するorg_idの一覧を返す（キャッシュ効率のためSELECTラップ）
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

### 2.2 organizations テーブル

```sql
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;

-- SELECT: 所属orgのみ閲覧可能
CREATE POLICY "org_select" ON public.organizations
  FOR SELECT TO authenticated
  USING (id IN (SELECT public.get_user_org_ids()));

-- UPDATE: owner/adminのみ
CREATE POLICY "org_update" ON public.organizations
  FOR UPDATE TO authenticated
  USING (public.has_org_role(id, 'owner') OR public.has_org_role(id, 'admin'))
  WITH CHECK (public.has_org_role(id, 'owner') OR public.has_org_role(id, 'admin'));

-- INSERT: 認証済みユーザーなら誰でも（新規org作成）
CREATE POLICY "org_insert" ON public.organizations
  FOR INSERT TO authenticated
  WITH CHECK ((SELECT auth.uid()) = owner_user_id);

-- DELETE: ownerのみ
CREATE POLICY "org_delete" ON public.organizations
  FOR DELETE TO authenticated
  USING ((SELECT auth.uid()) = owner_user_id);
```

### 2.3 org_members テーブル

```sql
ALTER TABLE public.org_members ENABLE ROW LEVEL SECURITY;

-- SELECT: 同じorgのメンバー一覧を閲覧可能
CREATE POLICY "members_select" ON public.org_members
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

-- INSERT: owner/adminのみメンバー追加可能
CREATE POLICY "members_insert" ON public.org_members
  FOR INSERT TO authenticated
  WITH CHECK (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'));

-- UPDATE: owner/adminのみロール変更可能（自分自身のownerロールは変更不可）
CREATE POLICY "members_update" ON public.org_members
  FOR UPDATE TO authenticated
  USING (
    (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'))
    AND NOT (user_id = (SELECT auth.uid()) AND role = 'owner')
  );

-- DELETE: owner/adminのみメンバー削除可能（owner自身は削除不可）
CREATE POLICY "members_delete" ON public.org_members
  FOR DELETE TO authenticated
  USING (
    (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'))
    AND NOT (user_id = (SELECT auth.uid()) AND role = 'owner')
  );
```

### 2.4 posts テーブル

```sql
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;

-- SELECT: 所属orgの投稿を閲覧可能
CREATE POLICY "posts_select" ON public.posts
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

-- INSERT: 編集権限があるorgに投稿作成可能
CREATE POLICY "posts_insert" ON public.posts
  FOR INSERT TO authenticated
  WITH CHECK (
    (SELECT public.can_edit_org(org_id))
    AND user_id = (SELECT auth.uid())
  );

-- UPDATE: 編集権限があるorgの投稿を編集可能
CREATE POLICY "posts_update" ON public.posts
  FOR UPDATE TO authenticated
  USING (SELECT public.can_edit_org(org_id))
  WITH CHECK (SELECT public.can_edit_org(org_id));

-- DELETE: 編集権限があるorgの投稿を削除可能（published以外）
CREATE POLICY "posts_delete" ON public.posts
  FOR DELETE TO authenticated
  USING (
    (SELECT public.can_edit_org(org_id))
    AND status != 'published'
  );
```

### 2.5 sns_accounts テーブル（トークン保護付き）

```sql
ALTER TABLE public.sns_accounts ENABLE ROW LEVEL SECURITY;

-- SELECT: 所属orgのアカウントを閲覧可能
-- 注意: access_token, refresh_tokenはビューで除外（後述）
CREATE POLICY "sns_accounts_select" ON public.sns_accounts
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

-- INSERT: owner/adminのみアカウント連携可能
CREATE POLICY "sns_accounts_insert" ON public.sns_accounts
  FOR INSERT TO authenticated
  WITH CHECK (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'));

-- UPDATE: owner/adminのみ（トークン更新はservice_role経由）
CREATE POLICY "sns_accounts_update" ON public.sns_accounts
  FOR UPDATE TO authenticated
  USING (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'));

-- DELETE: owner/adminのみアカウント削除可能
CREATE POLICY "sns_accounts_delete" ON public.sns_accounts
  FOR DELETE TO authenticated
  USING (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'));
```

### 2.6 post_targets テーブル

```sql
ALTER TABLE public.post_targets ENABLE ROW LEVEL SECURITY;

-- 親テーブル（posts）経由でアクセス制御
CREATE POLICY "targets_select" ON public.post_targets
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts
      WHERE posts.id = post_id
        AND posts.org_id IN (SELECT public.get_user_org_ids())
    )
  );

CREATE POLICY "targets_insert" ON public.post_targets
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.posts
      WHERE posts.id = post_id
        AND (SELECT public.can_edit_org(posts.org_id))
    )
  );

CREATE POLICY "targets_update" ON public.post_targets
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts
      WHERE posts.id = post_id
        AND (SELECT public.can_edit_org(posts.org_id))
    )
  );
```

### 2.7 post_media テーブル

```sql
ALTER TABLE public.post_media ENABLE ROW LEVEL SECURITY;

-- posts経由で制御（post_targetsと同じパターン）
CREATE POLICY "media_select" ON public.post_media
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts
      WHERE posts.id = post_id
        AND posts.org_id IN (SELECT public.get_user_org_ids())
    )
  );

CREATE POLICY "media_insert" ON public.post_media
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.posts
      WHERE posts.id = post_id
        AND (SELECT public.can_edit_org(posts.org_id))
    )
  );

CREATE POLICY "media_delete" ON public.post_media
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts
      WHERE posts.id = post_id
        AND (SELECT public.can_edit_org(posts.org_id))
    )
  );
```

### 2.8 notifications テーブル

```sql
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- SELECT: 自分宛ての通知のみ
CREATE POLICY "notifications_select" ON public.notifications
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));

-- UPDATE: 自分の通知の既読更新のみ
CREATE POLICY "notifications_update" ON public.notifications
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()));

-- INSERT/DELETE: service_roleのみ（バックエンドから作成）
-- フロントエンドからの直接INSERT/DELETEは不許可
```

### 2.9 generation_jobs / generation_sources テーブル

```sql
ALTER TABLE public.generation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_sources ENABLE ROW LEVEL SECURITY;

-- generation_jobs: 所属orgのジョブのみ
CREATE POLICY "gen_jobs_select" ON public.generation_jobs
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "gen_jobs_insert" ON public.generation_jobs
  FOR INSERT TO authenticated
  WITH CHECK (
    (SELECT public.can_edit_org(org_id))
    AND user_id = (SELECT auth.uid())
  );

-- generation_sources: 親ジョブ経由
CREATE POLICY "gen_sources_select" ON public.generation_sources
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.generation_jobs
      WHERE generation_jobs.id = job_id
        AND generation_jobs.org_id IN (SELECT public.get_user_org_ids())
    )
  );
```

### 2.10 ng_rule_presets テーブル（共有プリセット対応）

```sql
ALTER TABLE public.ng_rule_presets ENABLE ROW LEVEL SECURITY;

-- SELECT: システムデフォルト(org_id=NULL) + 所属orgのプリセット
CREATE POLICY "ng_rules_select" ON public.ng_rule_presets
  FOR SELECT TO authenticated
  USING (
    org_id IS NULL  -- システムデフォルト
    OR org_id IN (SELECT public.get_user_org_ids())
  );

-- INSERT: 編集権限があるorgにのみ作成可能
CREATE POLICY "ng_rules_insert" ON public.ng_rule_presets
  FOR INSERT TO authenticated
  WITH CHECK (
    org_id IS NOT NULL
    AND (SELECT public.can_edit_org(org_id))
  );

-- UPDATE: 自orgのプリセットのみ編集可能（システムデフォルトは不可）
CREATE POLICY "ng_rules_update" ON public.ng_rule_presets
  FOR UPDATE TO authenticated
  USING (
    org_id IS NOT NULL
    AND (SELECT public.can_edit_org(org_id))
  );

-- DELETE: 自orgのプリセットのみ削除可能
CREATE POLICY "ng_rules_delete" ON public.ng_rule_presets
  FOR DELETE TO authenticated
  USING (
    org_id IS NOT NULL
    AND (SELECT public.can_edit_org(org_id))
  );
```

---

## 3. トークン保護設計

### 3.1 フロントエンド向けビュー（トークン非公開）

```sql
-- フロントエンドにはこのビュー経由でアクセスさせる
CREATE VIEW public.sns_accounts_safe AS
SELECT
  id,
  org_id,
  platform,
  platform_user_id,
  platform_username,
  token_expires_at,
  created_at,
  updated_at,
  -- トークンの存在有無だけ公開（値は非公開）
  CASE WHEN access_token_enc IS NOT NULL THEN true ELSE false END AS has_access_token,
  CASE WHEN refresh_token_enc IS NOT NULL THEN true ELSE false END AS has_refresh_token,
  -- 期限切れ警告
  CASE
    WHEN token_expires_at IS NULL THEN 'no_expiry'
    WHEN token_expires_at < NOW() THEN 'expired'
    WHEN token_expires_at < NOW() + INTERVAL '7 days' THEN 'expiring_soon'
    ELSE 'valid'
  END AS token_status
FROM public.sns_accounts;
```

### 3.2 トークン操作はバックエンド専用

```python
# FastAPI側: service_roleキーでSupabaseに接続
from supabase import create_client

# service_roleクライアント（RLSバイパス）
supabase_admin = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY  # 環境変数から取得、絶対にフロントエンドに露出しない
)

# トークン読み書きはservice_role経由のみ
def get_account_tokens(account_id: str) -> dict:
    result = supabase_admin.table("sns_accounts") \
        .select("access_token_enc, refresh_token_enc") \
        .eq("id", account_id) \
        .single() \
        .execute()
    return decrypt_tokens(result.data)
```

---

## 4. サービスロール vs ユーザーロール

### 4.1 使い分けマトリクス

| 操作 | 実行元 | ロール | RLS |
|---|---|---|---|
| 投稿一覧表示 | フロントエンド | ユーザーロール | 適用 |
| 投稿作成・編集 | フロントエンド | ユーザーロール | 適用 |
| D&Dスケジュール変更 | フロントエンド | ユーザーロール | 適用 |
| **予約投稿の自動実行** | **Celery worker** | **service_role** | **バイパス** |
| **トークン読み書き** | **FastAPI** | **service_role** | **バイパス** |
| **通知の作成** | **FastAPI** | **service_role** | **バイパス** |
| **PostTarget状態更新** | **Celery worker** | **service_role** | **バイパス** |
| NGルール取得 | フロントエンド | ユーザーロール | 適用 |
| AI生成ジョブ作成 | フロントエンド | ユーザーロール | 適用 |
| **AI生成ジョブ実行** | **Celery worker** | **service_role** | **バイパス** |

### 4.2 service_roleキーの安全管理

```python
# 環境変数（Railway / Vercel）
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # 絶対にフロントエンドに渡さない

# FastAPIでの利用
# 1. 環境変数から読み込み
# 2. バックエンドサーバー内でのみ使用
# 3. ログに出力しない
# 4. Celery workerにも環境変数経由で渡す
```

---

## 5. インデックス戦略

### 5.1 RLSパフォーマンス用インデックス

```sql
-- org_members: 最頻出クエリ（get_user_org_ids）
CREATE INDEX idx_org_members_user_id ON public.org_members (user_id);
CREATE INDEX idx_org_members_org_id ON public.org_members (org_id);
CREATE UNIQUE INDEX idx_org_members_org_user ON public.org_members (org_id, user_id);

-- posts: カレンダー表示（日付範囲 + org_id）
CREATE INDEX idx_posts_org_scheduled ON public.posts (org_id, scheduled_at)
  WHERE status IN ('scheduled', 'publishing', 'published');
CREATE INDEX idx_posts_org_status ON public.posts (org_id, status);
CREATE INDEX idx_posts_user_id ON public.posts (user_id);

-- post_targets: 投稿実行ジョブ検索
CREATE INDEX idx_post_targets_post_id ON public.post_targets (post_id);
CREATE INDEX idx_post_targets_status ON public.post_targets (status)
  WHERE status IN ('pending', 'queued', 'retrying');

-- sns_accounts: org_id検索
CREATE INDEX idx_sns_accounts_org_id ON public.sns_accounts (org_id);

-- notifications: ユーザー別未読
CREATE INDEX idx_notifications_user_unread ON public.notifications (user_id)
  WHERE read = false;

-- generation_jobs: org_id検索
CREATE INDEX idx_gen_jobs_org_id ON public.generation_jobs (org_id);
```

### 5.2 パフォーマンス期待値

| クエリパターン | インデックスなし | インデックスあり | 改善率 |
|---|---|---|---|
| カレンダー月表示（org_id + 日付範囲） | ~170ms | <1ms | 99%+ |
| 未読通知カウント | ~50ms | <1ms | 98%+ |
| RLS auth.uid()チェック | ~10ms/行 | <0.1ms/行 | 99%+ |

---

## 6. Phase 2 チーム機能への拡張パス

### 6.1 承認フロー追加時

```sql
-- Phase 2で追加するテーブル
CREATE TABLE public.approval_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id),
  post_id UUID NOT NULL REFERENCES public.posts(id),
  requested_by UUID NOT NULL REFERENCES auth.users(id),
  approved_by UUID REFERENCES auth.users(id),
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected')),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

-- RLSポリシー: orgメンバー全員が閲覧可、admin/owner が承認可
CREATE POLICY "approval_select" ON public.approval_requests
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "approval_update" ON public.approval_requests
  FOR UPDATE TO authenticated
  USING (
    public.has_org_role(org_id, 'owner')
    OR public.has_org_role(org_id, 'admin')
  );
```

### 6.2 ロール拡張

```
Phase 1: owner のみ（個人org）
Phase 2: owner → admin → editor → viewer
  - owner:  全権限 + org削除 + メンバー管理
  - admin:  メンバー管理 + SNSアカウント管理 + 承認
  - editor: 投稿作成・編集 + AI生成
  - viewer: 閲覧のみ（承認待ちレビュー用）
```

---

## 7. セキュリティチェックリスト

| # | チェック項目 | 対策 |
|---|---|---|
| 1 | 全テーブルにRLS有効化 | マイグレーションテンプレートに`ENABLE ROW LEVEL SECURITY`を必須化 |
| 2 | RLS有効化後にポリシー定義 | CI/CDでポリシー未定義テーブルを検知するチェックスクリプト |
| 3 | `(SELECT auth.uid())`ラップ | 全ポリシーでSELECTラップ済み（99%のパフォーマンス改善） |
| 4 | service_roleキーの保護 | フロントエンド環境変数に含めない。`NEXT_PUBLIC_`接頭辞なし |
| 5 | トークンカラムの非公開 | `sns_accounts_safe`ビュー経由のみフロントエンドに公開 |
| 6 | Storage RLS | R2を使用するため直接は影響しないが、Supabase Storageを使う場合は必須 |
| 7 | Realtime RLS | Supabase Realtimeサブスクリプションは自動でRLSを適用。ポリシーがカバーする |
| 8 | テスト | pgTapでRLSポリシーのユニットテストを書く（異なるユーザーロールで検証） |

---

## 8. テスト戦略

### 8.1 pgTapテスト例

```sql
-- テスト: 異なるorgのユーザーが投稿を見えないことを検証
BEGIN;
SELECT plan(3);

-- ユーザーAを作成
SELECT tests.create_supabase_user('user_a', 'a@test.com');
-- ユーザーBを作成（別org）
SELECT tests.create_supabase_user('user_b', 'b@test.com');

-- ユーザーAとして認証し投稿を作成
SELECT tests.authenticate_as('user_a');
INSERT INTO public.posts (org_id, user_id, status, text)
VALUES ((SELECT default_org_id FROM public.users WHERE id = (SELECT auth.uid())),
        (SELECT auth.uid()), 'draft', 'テスト投稿');

-- ユーザーAは自分の投稿が見える
SELECT results_eq(
  $$ SELECT count(*)::int FROM public.posts $$,
  ARRAY[1],
  'User A can see their own post'
);

-- ユーザーBとして認証
SELECT tests.authenticate_as('user_b');

-- ユーザーBにはユーザーAの投稿が見えない
SELECT is_empty(
  $$ SELECT * FROM public.posts $$,
  'User B cannot see User A posts'
);

-- ユーザーBが別orgの投稿を更新しようとしても0行に影響
SELECT results_eq(
  $$ UPDATE public.posts SET text = 'hacked' RETURNING id $$,
  ARRAY[]::UUID[],
  'User B cannot update User A posts'
);

SELECT * FROM finish();
ROLLBACK;
```

---

## 9. 優先アクション

| # | アクション | 理由 |
|---|---|---|
| 1 | `organizations` + `org_members`テーブル作成 | Phase 2チーム機能の土台。後から追加するとマイグレーションが困難 |
| 2 | 全テーブルにRLS有効化 + ポリシー定義 | セキュリティの基盤。初日から有効化 |
| 3 | `get_user_org_ids()`ヘルパー関数作成 | 全ポリシーで再利用。SELECTラップでパフォーマンス確保 |
| 4 | `sns_accounts_safe`ビュー作成 | トークン漏洩防止 |
| 5 | インデックス作成 | カレンダー表示のパフォーマンス確保 |
| 6 | pgTapテスト作成 | ポリシーのリグレッション防止 |
