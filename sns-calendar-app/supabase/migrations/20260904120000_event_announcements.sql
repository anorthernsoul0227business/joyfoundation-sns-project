-- イベント告知を仕組みにする。
--
-- 2026-09-04 康二郎さんの要望:
--   ・カレンダーに予定が入った時点で告知記事を作る
--   ・告知開始日は圭一郎さんが必ず判断する（既定値はあるが上書きできる）
--   ・X と Instagram は「前日」に必ず投稿する
--
-- 前提として分かったこと: 今後の予定29件のうち「スターライトヒーリング」だけで
-- 10公演あり、1公演ごとに告知すると9月だけで毎日3〜4回投稿になる。
-- 同じ催しはまとめて1つの告知として扱う必要がある。

-- 同じ催しをまとめる鍵。タイトルの表記ゆれを均したもの
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS series_key TEXT;

-- 告知を始める日。圭一郎さんが決める。NULL なら開催までの日数から既定値を使う
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS announce_from DATE;

-- 圭一郎さんが告知の方針を書く欄（「今回は早めに」「今回は告知しない」など）
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS announce_note TEXT;

-- 告知しない、と決めた催し
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS announce_skip BOOLEAN NOT NULL DEFAULT false;

-- 告知記事を作った日時。二度作らないための目印
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS articles_generated_at TIMESTAMPTZ;

COMMENT ON COLUMN public.events.series_key IS
  '同じ催しをまとめる鍵。複数公演を1つの告知として扱う';
COMMENT ON COLUMN public.events.announce_from IS
  '告知を始める日。圭一郎さんの判断が優先され、未設定なら開催までの日数から決める';

CREATE INDEX IF NOT EXISTS idx_events_series ON public.events (org_id, series_key, starts_at);

-- 記事がどの催しの告知かを持たせる。前日投稿を必ず確保するために使う
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS event_series_key TEXT;

-- 告知の役割。'day_before' は他の予定より優先して必ず投稿する
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS announce_role VARCHAR(20)
  CHECK (announce_role IS NULL OR announce_role IN ('early', 'middle', 'late', 'day_before'));

COMMENT ON COLUMN public.articles.announce_role IS
  '告知記事の役割。day_before は前日投稿で、他の予定と重なっても優先する';
