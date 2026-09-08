-- 見回りで見つけた「やること」と、その解決案を持つ。
--
-- 2026-09-08 康二郎さんの構想:
--   ・メモや圭一郎さんの更新を1日2回見回って、やることを見つける
--   ・見つけたら AI が「こう解決します」という案を出す
--   ・押すと案が開き、承認すればそのまま実行。却下なら人が解決するか、
--     思いつきメモに書いてもらって作り直す
--
-- 承認したら実行、を安全にするために、書き方の決まりは
-- コードではなく writing_rules に置く。承認しても行が1つ増えるだけで、
-- コードの書き換えも再デプロイも起きない。

CREATE TABLE IF NOT EXISTS public.tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,

  -- どこから見つけたか
  source VARCHAR(20) NOT NULL
    CHECK (source IN ('idea', 'fix_request', 'owner_input', 'schedule', 'system')),
  -- 元になったメモや記事。同じものから二重に作らないための目印でもある
  source_key TEXT NOT NULL,

  title TEXT NOT NULL,
  detail TEXT,

  status VARCHAR(20) NOT NULL DEFAULT 'open'
    CHECK (status IN (
      'open',      -- 見つけたばかり。まだ案がない
      'proposed',  -- AI が案を出した。承認まち
      'approved',  -- 承認された。実行まち
      'done',      -- 実行し終えた
      'rejected',  -- 却下された。作り直すか人が解決する
      'dismissed'  -- やらないと決めた
    )),

  -- AI の解決案。人が読む文章
  proposal TEXT,
  -- 承認されたときに何をするか。実行できる種類だけを許す
  proposal_kind VARCHAR(30)
    CHECK (proposal_kind IS NULL OR proposal_kind IN (
      'writing_rule',   -- 書き方の決まりを足す
      'reschedule',     -- 投稿日を決め直す
      'rewrite_article',-- 記事を書き直す
      'reply_only',     -- 返事をするだけ
      'manual'          -- 人がやる必要がある
    )),
  -- 実行に必要な値（決まりの本文、記事番号など）
  proposal_payload JSONB,

  decided_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  decided_at TIMESTAMPTZ,
  decision_note TEXT,
  done_at TIMESTAMPTZ,
  result_note TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT tasks_decided_requires_time CHECK (
    (status NOT IN ('approved', 'rejected', 'dismissed')) OR decided_at IS NOT NULL
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_source ON public.tasks (org_id, source, source_key);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON public.tasks (org_id, status, created_at DESC);

CREATE TRIGGER tasks_set_updated_at
  BEFORE UPDATE ON public.tasks
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMENT ON TABLE public.tasks IS
  '見回りで見つけたやること。承認すると proposal_kind に応じて実行する';


-- 記事の書き方の決まり。圭一郎さんの指摘から育てていく。
-- コードに書くとAIが承認のたびにコードを書き換えることになるため、ここに持つ
CREATE TABLE IF NOT EXISTS public.writing_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,

  -- どの生成に効かせるか
  scope VARCHAR(20) NOT NULL DEFAULT 'both'
    CHECK (scope IN ('weekly', 'event', 'both')),
  body TEXT NOT NULL,
  -- なぜこの決まりができたか。圭一郎さんの言葉をそのまま残す
  origin TEXT,
  source_task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL,
  active BOOLEAN NOT NULL DEFAULT true,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_writing_rules_active
  ON public.writing_rules (org_id, active, scope);

CREATE TRIGGER writing_rules_set_updated_at
  BEFORE UPDATE ON public.writing_rules
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMENT ON TABLE public.writing_rules IS
  '記事の書き方の決まり。承認された案がここに積まれ、生成時にプロンプトへ足される';


-- RLS
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.writing_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tasks_select" ON public.tasks FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "tasks_insert" ON public.tasks FOR INSERT TO authenticated
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "tasks_update" ON public.tasks FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id)) WITH CHECK (public.can_edit_org(org_id));

CREATE POLICY "writing_rules_select" ON public.writing_rules FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "writing_rules_insert" ON public.writing_rules FOR INSERT TO authenticated
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "writing_rules_update" ON public.writing_rules FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id)) WITH CHECK (public.can_edit_org(org_id));
