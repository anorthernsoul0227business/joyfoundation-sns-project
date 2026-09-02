-- 承認された記事を、いつ投稿するか決めて記録する。
--
-- 2026-09-02 に判明した事情:
--   ・投稿は 6/16 から止まっている。承認と投稿キューの間を人が繋いでいて、途絶えた
--   ・承認待ち57件のうち19件が本文の中で具体的な日付に触れている（9/5 の公演など）
--   ・圭一郎さんは週に一度まとめて承認される見込み。「承認の翌日」では期日に間に合わない
--   ・note には自動投稿の仕組みが無い（X と Instagram のみ）

-- 本文から読み取ったイベント開催日。ここが入っている記事は期日から逆算して投稿する
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS event_date DATE;

-- 実際に投稿する日時。日付だけの scheduled_date と違い時刻まで持つ
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;

-- 手で投稿する必要がある媒体（note）のために、投稿済みにした人を残す
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS posted_manually_by UUID
  REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_status_check;
ALTER TABLE public.articles ADD CONSTRAINT articles_status_check
  CHECK (status IN (
    'ai_draft',
    'needs_check',
    'staff_ok',
    'needs_fix',
    'revised',
    'approved',     -- 圭一郎OK。まだ投稿日が決まっていない
    'scheduled',    -- 投稿日時が決まり、キューに入った
    'published',
    'missed'        -- イベント当日を過ぎてしまい、もう出せない
  ));

COMMENT ON COLUMN public.articles.event_date IS
  '本文が触れているイベントの開催日。過ぎたら投稿してはいけない';
COMMENT ON COLUMN public.articles.scheduled_at IS
  '投稿予定日時。イベント記事は開催日から逆算、それ以外は承認の翌日から順に';

CREATE INDEX IF NOT EXISTS idx_articles_scheduled
  ON public.articles (org_id, scheduled_at) WHERE status = 'scheduled';
