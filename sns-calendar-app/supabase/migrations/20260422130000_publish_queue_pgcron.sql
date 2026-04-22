-- ARCH-001: publish_queue テーブル + pg_cron で予約投稿の enqueue
-- 目的: Celery Beat (常駐) を不要にし、DB 内で時刻到達判定を完結させる
-- Depends on: 20260420010431_posts_schema.sql

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.publish_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  scheduled_at TIMESTAMPTZ NOT NULL,
  locked_at TIMESTAMPTZ,
  locked_by TEXT,
  attempts INT NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  CONSTRAINT unique_post_queue UNIQUE (post_id)
);

COMMENT ON TABLE public.publish_queue IS
  'ARCH-001: 予約時刻到達した posts を enqueue する中間キュー。'
  'GitHub Actions Cron 経由で FastAPI /internal/publish/flush が lock → 投稿 → complete する。';

CREATE INDEX IF NOT EXISTS idx_publish_queue_pending
  ON public.publish_queue (scheduled_at)
  WHERE locked_at IS NULL AND completed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_publish_queue_org
  ON public.publish_queue (org_id);

-- RLS: クライアントは直接触らない。service_role だけ全操作可。
ALTER TABLE public.publish_queue ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS publish_queue_service_all ON public.publish_queue;
CREATE POLICY publish_queue_service_all
  ON public.publish_queue
  FOR ALL
  USING ((auth.jwt() ->> 'role') = 'service_role')
  WITH CHECK ((auth.jwt() ->> 'role') = 'service_role');

-- pg_cron: 毎分、予約時刻到達の posts を publish_queue に enqueue
-- 重複挿入は UNIQUE 制約で防止
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
             WHERE n.nspname = 'cron' AND p.proname = 'schedule') THEN
    PERFORM cron.unschedule('enqueue-scheduled-posts')
    WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'enqueue-scheduled-posts');

    PERFORM cron.schedule(
      'enqueue-scheduled-posts',
      '* * * * *',
      $SQL$
      INSERT INTO public.publish_queue (post_id, org_id, scheduled_at)
      SELECT p.id, p.org_id, p.scheduled_at
      FROM public.posts p
      WHERE p.status = 'scheduled'
        AND p.scheduled_at IS NOT NULL
        AND p.scheduled_at <= NOW()
      ON CONFLICT (post_id) DO NOTHING;
      $SQL$
    );
  END IF;
END
$$;
