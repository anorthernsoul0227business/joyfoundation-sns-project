-- WEB-027: notifications (リアルタイム通知 + 履歴)
-- Depends on: 20260418100000_initial_schema.sql, 20260420010431_posts_schema.sql

CREATE TABLE public.notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  org_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  kind VARCHAR(30) NOT NULL
    CHECK (kind IN ('post_published', 'post_failed', 'post_partial', 'system')),
  title TEXT NOT NULL,
  body TEXT,
  related_post_id UUID REFERENCES public.posts(id) ON DELETE SET NULL,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.notifications IS
  '通知履歴。post_published/failed 等の種類別に発火し、WebSocket でリアルタイム配信される';

CREATE INDEX idx_notifications_user_created
  ON public.notifications (user_id, created_at DESC);

CREATE INDEX idx_notifications_user_unread
  ON public.notifications (user_id, read_at)
  WHERE read_at IS NULL;

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY notifications_user_select
  ON public.notifications
  FOR SELECT
  USING (user_id = (SELECT auth.uid()));

CREATE POLICY notifications_user_update
  ON public.notifications
  FOR UPDATE
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (user_id = (SELECT auth.uid()));
