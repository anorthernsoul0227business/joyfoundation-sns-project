-- WEB-010: posts / post_targets / post_media / sns_accounts + RLS + indexes
-- Depends on: 20260418100000_initial_schema.sql, 20260418113000_rls_policies.sql

-- =============================================================================
-- 1. posts (投稿本体)
-- =============================================================================
CREATE TABLE public.posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  status VARCHAR(20) NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'scheduled', 'publishing', 'published', 'failed', 'archived')),
  scheduled_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  content_text TEXT NOT NULL DEFAULT '',
  ai_generated BOOLEAN NOT NULL DEFAULT false,
  prompt_version_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT posts_scheduled_requires_time CHECK (
    status <> 'scheduled' OR scheduled_at IS NOT NULL
  ),
  CONSTRAINT posts_published_requires_time CHECK (
    status <> 'published' OR published_at IS NOT NULL
  )
);

COMMENT ON TABLE public.posts IS
  '投稿本体。scheduled_at で予約投稿、Celeryが status=scheduled を監視して発火';

CREATE TRIGGER posts_set_updated_at
  BEFORE UPDATE ON public.posts
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 2. post_targets (投稿先SNSごとの状態)
-- =============================================================================
CREATE TABLE public.post_targets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
  platform VARCHAR(20) NOT NULL
    CHECK (platform IN ('x', 'ig', 'note', 'youtube', 'line')),
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'publishing', 'published', 'failed', 'skipped')),
  published_at TIMESTAMPTZ,
  platform_post_id TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (post_id, platform)
);

COMMENT ON TABLE public.post_targets IS
  '投稿先SNSごとの状態。1つの投稿を複数SNSへ配信する場合、各行が実行単位';

CREATE TRIGGER post_targets_set_updated_at
  BEFORE UPDATE ON public.post_targets
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 3. post_media (投稿の添付画像)
-- =============================================================================
CREATE TABLE public.post_media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  mime_type VARCHAR(50) NOT NULL,
  width INT,
  height INT,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.post_media IS
  '投稿の画像添付。storage_path は Supabase Storage / R2 の object key';


-- =============================================================================
-- 4. sns_accounts (連携SNSアカウント、トークン保管)
-- =============================================================================
CREATE TABLE public.sns_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  platform VARCHAR(20) NOT NULL
    CHECK (platform IN ('x', 'ig', 'note', 'youtube', 'line')),
  handle TEXT NOT NULL,
  display_name TEXT,
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (org_id, platform, handle)
);

COMMENT ON TABLE public.sns_accounts IS
  '連携SNSアカウントのトークン保管。RLSでフロント公開を完全に遮断し、sns_accounts_safe ビュー経由でメタ情報のみ露出';

CREATE TRIGGER sns_accounts_set_updated_at
  BEFORE UPDATE ON public.sns_accounts
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 5. sns_accounts_safe VIEW (APP_DESIGN_SPEC 決定事項#14)
-- =============================================================================
CREATE OR REPLACE VIEW public.sns_accounts_safe
WITH (security_invoker = true) AS
SELECT
  id,
  org_id,
  platform,
  handle,
  display_name,
  expires_at,
  is_active,
  created_at,
  updated_at
FROM public.sns_accounts;

COMMENT ON VIEW public.sns_accounts_safe IS
  'トークン列を除外した公開ビュー。フロントエンドはこのビューのみSELECT可、sns_accounts本体は不可';


-- =============================================================================
-- 6. インデックス (RLS_DESIGN.md セクション8 準拠 + カレンダー表示最適化)
-- =============================================================================
-- posts: カレンダー/下書き一覧の最頻出クエリ
CREATE INDEX idx_posts_org_scheduled ON public.posts (org_id, scheduled_at)
  WHERE status = 'scheduled';
CREATE INDEX idx_posts_org_status ON public.posts (org_id, status);
CREATE INDEX idx_posts_user ON public.posts (user_id);

-- post_targets: Celery スキャン + ステータス参照
CREATE INDEX idx_post_targets_post ON public.post_targets (post_id);
CREATE INDEX idx_post_targets_platform_status ON public.post_targets (platform, status);

-- post_media: post 経由の取得
CREATE INDEX idx_post_media_post ON public.post_media (post_id, sort_order);

-- sns_accounts: org/platform引き
CREATE INDEX idx_sns_accounts_org_platform ON public.sns_accounts (org_id, platform)
  WHERE is_active = true;


-- =============================================================================
-- 7. RLS ポリシー
-- =============================================================================

-- 7.1 posts -----------------------------------------------------------------
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "posts_select" ON public.posts
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "posts_insert" ON public.posts
  FOR INSERT TO authenticated
  WITH CHECK (
    public.can_edit_org(org_id)
    AND user_id = (SELECT auth.uid())
  );

CREATE POLICY "posts_update" ON public.posts
  FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id))
  WITH CHECK (public.can_edit_org(org_id));

CREATE POLICY "posts_delete" ON public.posts
  FOR DELETE TO authenticated
  USING (
    public.can_edit_org(org_id)
    AND status <> 'published'
  );


-- 7.2 post_targets ----------------------------------------------------------
ALTER TABLE public.post_targets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "post_targets_select" ON public.post_targets
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_targets.post_id
        AND p.org_id IN (SELECT public.get_user_org_ids())
    )
  );

CREATE POLICY "post_targets_insert" ON public.post_targets
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_targets.post_id
        AND public.can_edit_org(p.org_id)
    )
  );

CREATE POLICY "post_targets_update" ON public.post_targets
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_targets.post_id
        AND public.can_edit_org(p.org_id)
    )
  );

CREATE POLICY "post_targets_delete" ON public.post_targets
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_targets.post_id
        AND public.can_edit_org(p.org_id)
        AND p.status <> 'published'
    )
  );


-- 7.3 post_media ------------------------------------------------------------
ALTER TABLE public.post_media ENABLE ROW LEVEL SECURITY;

CREATE POLICY "post_media_select" ON public.post_media
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_media.post_id
        AND p.org_id IN (SELECT public.get_user_org_ids())
    )
  );

CREATE POLICY "post_media_insert" ON public.post_media
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_media.post_id
        AND public.can_edit_org(p.org_id)
    )
  );

CREATE POLICY "post_media_update" ON public.post_media
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_media.post_id
        AND public.can_edit_org(p.org_id)
    )
  );

CREATE POLICY "post_media_delete" ON public.post_media
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.posts p
      WHERE p.id = post_media.post_id
        AND public.can_edit_org(p.org_id)
    )
  );


-- 7.4 sns_accounts ----------------------------------------------------------
-- RLSは有効化するが authenticated 向け policy は定義しない。
-- service_role のみ直接操作可能。フロントは sns_accounts_safe 経由のみ。
ALTER TABLE public.sns_accounts ENABLE ROW LEVEL SECURITY;


-- 7.5 sns_accounts_safe ビュー
-- security_invoker = true なので、呼び出し元ロールで sns_accounts にアクセスする。
-- authenticated から sns_accounts 本体への policy がないため、このままでは見えない。
-- authenticated 向けに本体 SELECT policy を「トークン列を含まない形でしか読めない」
-- ようにするのは列レベルでは困難なので、明示的に select policy を追加して
-- ビュー経由の SELECT のみ許可する（INSERT/UPDATE/DELETE policy は定義しない）。
CREATE POLICY "sns_accounts_select_for_safe_view" ON public.sns_accounts
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));

-- 本体のトークン列は RLS policy だけでは列単位でブロックできないため、
-- 列レベル GRANT で authenticated からのトークン列アクセスを遮断する。
REVOKE ALL ON public.sns_accounts FROM authenticated, anon;
GRANT SELECT (id, org_id, platform, handle, display_name, expires_at, is_active, created_at, updated_at)
  ON public.sns_accounts TO authenticated;

-- sns_accounts_safe ビューは全列参照可能
GRANT SELECT ON public.sns_accounts_safe TO authenticated;
