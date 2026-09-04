-- 圭一郎さんの思いつきメモに返事を返せるようにする。
--
-- 2026-09-04: 圭一郎さんから「言葉づかいが頼りなく聞こえる」という指摘が届いたが、
-- 状態は「届いています」のままで、読んだことも反映したことも本人に伝わらなかった。
-- 指摘 → ルール化 → 反映を知らせる、という一周が回るようにする。

ALTER TABLE public.ideas ADD COLUMN IF NOT EXISTS reply TEXT;
ALTER TABLE public.ideas ADD COLUMN IF NOT EXISTS replied_at TIMESTAMPTZ;

COMMENT ON COLUMN public.ideas.reply IS
  'メモへの返事。読んだこと、どう反映したかを圭一郎さんに伝える';

ALTER TABLE public.ideas DROP CONSTRAINT IF EXISTS ideas_status_check;
ALTER TABLE public.ideas ADD CONSTRAINT ideas_status_check
  CHECK (status IN (
    'new',       -- 届いています
    'read',      -- 読みました
    'reflected', -- 記事の作り方に反映しました
    'used',      -- 記事にしました
    'holding'    -- あたためています
  ));
