-- 記事を破棄できるようにする。
--
-- 2026-09-08 康二郎さんの要望:
--   ・日にち的にもう適していない、投稿の必要がないと判断した記事を破棄したい
--   ・破棄したものは1週間ほど残し、時間が過ぎたらアプリから消してよい
--
-- 元データは残す。理由:
--   ・週次ループは load_recent() で直近の記事を読み、同じ切り口が続かないように
--     している。破棄した記事を消すと、AI はそれを知らずに同じ角度の記事をまた作る。
--     「出さないと判断された」は、承認された記事と同じくらい価値がある情報
--   ・なぜ破棄したかは、書き方の決まりを育てる材料そのもの
--   ・記事169本の本文を合計しても98K文字（約300KB）。消して得られるものがない
--
-- 消すのはその記事専用の画像だけ（storage_path が drive/ で始まらないもの）。
-- Drive の写真は画像プールを複数記事で使い回しているため消してはいけない。

ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_status_check;
ALTER TABLE public.articles ADD CONSTRAINT articles_status_check
  CHECK (status IN (
    'ai_draft',
    'needs_check',
    'staff_ok',
    'needs_fix',
    'needs_owner_input',
    'revised',
    'approved',
    'scheduled',
    'published',
    'missed',
    'discarded'   -- 出さないと決めたもの
  ));

ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS discarded_at TIMESTAMPTZ;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS discard_reason TEXT;
-- 1週間たったらアプリから見えなくする。データは残す
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_discarded_requires_time;
ALTER TABLE public.articles ADD CONSTRAINT articles_discarded_requires_time
  CHECK (status <> 'discarded' OR discarded_at IS NOT NULL);

COMMENT ON COLUMN public.articles.discard_reason IS
  'なぜ出さないと判断したか。同じ切り口を繰り返さないため AI にも伝える';
COMMENT ON COLUMN public.articles.archived_at IS
  'アプリの一覧から外した日時。データ自体は残す';

CREATE INDEX IF NOT EXISTS idx_articles_discarded
  ON public.articles (org_id, discarded_at) WHERE status = 'discarded';
