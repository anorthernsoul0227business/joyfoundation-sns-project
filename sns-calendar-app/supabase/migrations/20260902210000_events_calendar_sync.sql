-- Google カレンダーを開催日の正本にする。
--
-- 2026-09-02: 圭一郎さん（keiichiro.kita@gmail.com）のカレンダーが読めるようになった。
-- スプレッドシートの「イベント予定」より新しく、11月・12月の予定も入っている。
-- 以後はカレンダーを取り込み、シートは費用などの補足だけに使う。

-- 取り込みの目印。同じ予定を二重に入れず、変更を上書きするために使う。
-- 繰り返し予定は singleEvents=true で1回ずつ別IDになるので、そのまま使える
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS google_event_id TEXT;

-- 条件付き（WHERE ...）にすると ON CONFLICT の対象として推論できない。
-- NULL 同士は重複とみなされないため、条件なしでも手入力の予定（google_event_id が
-- NULL）は何件でも入れられる
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_google_id
  ON public.events (org_id, google_event_id);

-- 「このイベントは何日前から告知するか」。イベントごとに変えられるようにする
-- （2026-09-02 康二郎さんの要望。公演は早めに、研修は直前に、など）
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS lead_days INT;

COMMENT ON COLUMN public.events.google_event_id IS
  'Google カレンダー側のID。取り込みの重複を防ぐ';
COMMENT ON COLUMN public.events.lead_days IS
  '開催の何日前に告知記事を投稿するか。NULL なら既定値（3日前）を使う';

CREATE INDEX IF NOT EXISTS idx_events_starts_at ON public.events (org_id, starts_at);
