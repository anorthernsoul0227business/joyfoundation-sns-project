-- 共有ボード: 圭一郎さんとの情報共有を1画面に統合するためのテーブル群
--
-- 背景:
--   スプレッドシート（週次_レビュー 18列 / イベント予定 / メール / NotebookLM）に
--   分散していた情報を Supabase に集約する。列が多く横スクロールが頻発し、
--   行が縦に伸びて記事を特定できない状態の解消が目的。
--
-- 依存: 20260418100000_initial_schema.sql（set_updated_at / organizations）
--       20260418113000_rls_policies.sql（get_user_org_ids / can_edit_org）
--
-- 備考: posts / post_targets / publish_queue は Cloud Run 版 publisher 専用で、
--       実際の投稿は Mac mini の launchd ジョブが行う。本マイグレーション以降、
--       投稿パイプラインの正は articles になる。posts は残すが使わない。


-- =============================================================================
-- 1. articles（記事のレビュー・承認）
--    スプレッドシート「週次_レビュー」タブの後継
-- =============================================================================
CREATE TABLE public.articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,

  -- シート由来の識別子（例: IG-2609-03）。週次ループが採番する
  article_no TEXT NOT NULL,
  week TEXT,

  platform VARCHAR(20) NOT NULL
    CHECK (platform IN ('x', 'ig', 'note', 'youtube', 'line')),
  scheduled_date DATE,

  -- 分級。A=確認済みカードの言い換えのみ / B=新しい組み合わせ / C=新規数値・医療表現
  grade CHAR(1) CHECK (grade IN ('A', 'B', 'C')),
  source_card_ids TEXT[] NOT NULL DEFAULT '{}',

  -- 一覧表示用。本文の【】見出しを週次ループが切り出して入れる
  title TEXT NOT NULL DEFAULT '',
  body_ai TEXT NOT NULL DEFAULT '',
  body_final TEXT,

  status VARCHAR(20) NOT NULL DEFAULT 'ai_draft'
    CHECK (status IN (
      'ai_draft',    -- AI下書き
      'needs_check', -- 要確認あり
      'staff_ok',    -- 康二郎OK（一次承認）
      'approved',    -- 圭一郎OK
      'needs_fix',   -- 要修正
      'scheduled',   -- 投稿予約
      'published'    -- 投稿済
    )),

  -- 圭一郎さんが普通の日本語で書く欄。2026-09-01 に修正種別プルダウンを廃止し、
  -- 分類（fix_type / fix_apply）は康二郎さんが後から付ける方式へ変更した
  fix_note TEXT,
  fix_type TEXT,   -- taxonomy.md の13コード（E1/E2/.../T1）。康二郎さんが後付け
  fix_apply VARCHAR(20) CHECK (fix_apply IN ('permanent', 'once', 'none')),

  image_reason TEXT,

  reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (org_id, article_no),

  -- 修正を求めるなら、どこを直すか必ず書かれている状態にする
  CONSTRAINT articles_needs_fix_requires_note CHECK (
    status <> 'needs_fix' OR (fix_note IS NOT NULL AND btrim(fix_note) <> '')
  ),
  CONSTRAINT articles_published_requires_time CHECK (
    status <> 'published' OR published_at IS NOT NULL
  )
);

COMMENT ON TABLE public.articles IS
  '記事のレビュー・承認。週次ループが ai_draft で作り、圭一郎さんが approved / needs_fix を決める';
COMMENT ON COLUMN public.articles.body_ai IS
  'AI原稿。圭一郎さんには上書きさせない（差分を残すため body_final と分けている）';
COMMENT ON COLUMN public.articles.fix_note IS
  '圭一郎さんの自由記入。分類コードは選ばせず、康二郎さんが fix_type に後付けする';

CREATE TRIGGER articles_set_updated_at
  BEFORE UPDATE ON public.articles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 2. article_reviews（承認・修正依頼の履歴）
--    シートは上書きで履歴が消えていたため、やり取りを行として残す
-- =============================================================================
CREATE TABLE public.article_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  reviewer_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  decision VARCHAR(20) NOT NULL
    CHECK (decision IN ('approve', 'request_fix')),
  note TEXT,
  -- 判断時点の本文。後から原稿が変わっても、何に対するOKだったかを追える
  body_snapshot TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.article_reviews IS
  '承認・修正依頼の履歴。articles.status は最新の decision を写したもの';


-- =============================================================================
-- 3. ideas（思いつきメモ）
-- =============================================================================
CREATE TABLE public.ideas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  author_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  body TEXT NOT NULL,
  source VARCHAR(20) NOT NULL DEFAULT 'web'
    CHECK (source IN ('web', 'voice', 'mail', 'line')),
  status VARCHAR(20) NOT NULL DEFAULT 'new'
    CHECK (status IN ('new', 'read', 'used', 'holding')),
  -- 記事になったらここで繋ぐ。「あの思いつきはどうなった」を追えるようにする
  linked_article_id UUID REFERENCES public.articles(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.ideas IS
  '圭一郎さんの思いつきメモ。一行でも投稿できることを優先し、必須項目は body だけ';

CREATE TRIGGER ideas_set_updated_at
  BEFORE UPDATE ON public.ideas
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 4. events（イベント情報）
--    スプレッドシート「イベント予定」タブの後継
-- =============================================================================
CREATE TABLE public.events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ,
  all_day BOOLEAN NOT NULL DEFAULT false,
  venue TEXT,
  price_text TEXT,
  url TEXT,
  description TEXT,

  -- 情報源。L1原本（チラシ・協会誌）と L4カレンダー のどちらが根拠かを追う
  source VARCHAR(20) NOT NULL DEFAULT 'other'
    CHECK (source IN ('l1_original', 'l4_calendar', 'mail', 'keiichiro', 'other')),
  -- 圭一郎さん確認済みか。カレンダーだけが根拠の予定を告知に使わないための歯止め
  confirmed_by_owner BOOLEAN NOT NULL DEFAULT false,
  confirmed_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT events_ends_after_starts CHECK (ends_at IS NULL OR ends_at >= starts_at),
  CONSTRAINT events_confirmed_requires_time CHECK (
    confirmed_by_owner = false OR confirmed_at IS NOT NULL
  )
);

COMMENT ON TABLE public.events IS
  'イベント情報。confirmed_by_owner が false のものは告知記事の根拠にしない';

CREATE TRIGGER events_set_updated_at
  BEFORE UPDATE ON public.events
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 5. shares（資料・お知らせの共有タイムライン）
--    メール / NotebookLM / LINE に散っていた情報共有の受け皿
-- =============================================================================
CREATE TABLE public.shares (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  author_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  kind VARCHAR(20) NOT NULL DEFAULT 'notice'
    CHECK (kind IN ('notice', 'document', 'link', 'question')),
  title TEXT NOT NULL,
  body TEXT,
  url TEXT,
  -- 質問に answered が付くまで一覧の上に出し続ける
  answered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.shares IS
  '資料・お知らせ・質問の共有タイムライン。kind=question は answered_at が付くまで未対応扱い';

CREATE TRIGGER shares_set_updated_at
  BEFORE UPDATE ON public.shares
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- 6. attachments（画像添付）
--    記事・イベント・共有・メモのどれにも画像を付けられるようにする
-- =============================================================================
CREATE TABLE public.attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  owner_type VARCHAR(20) NOT NULL
    CHECK (owner_type IN ('article', 'event', 'share', 'idea')),
  owner_id UUID NOT NULL,
  -- R2 のオブジェクトキーと公開URL。Mac mini の投稿ジョブは public_url を読む
  storage_path TEXT NOT NULL,
  public_url TEXT NOT NULL,
  mime_type VARCHAR(50) NOT NULL,
  width INT,
  height INT,
  sort_order INT NOT NULL DEFAULT 0,
  caption TEXT,
  -- Drive から取り込んだ場合の元ID。重複取り込みの検出に使う
  drive_file_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.attachments IS
  '画像添付。owner_type + owner_id で親を指す（FKは張らず、削除は各画面の責務）';

CREATE INDEX idx_attachments_owner ON public.attachments (owner_type, owner_id, sort_order);


-- =============================================================================
-- インデックス
-- =============================================================================
-- 「未対応だけ」が初期表示。org_id + status + 投稿予定日 で引く
CREATE INDEX idx_articles_org_status_date
  ON public.articles (org_id, status, scheduled_date DESC);
CREATE INDEX idx_articles_org_week ON public.articles (org_id, week);
CREATE INDEX idx_article_reviews_article ON public.article_reviews (article_id, created_at DESC);
CREATE INDEX idx_ideas_org_status ON public.ideas (org_id, status, created_at DESC);
CREATE INDEX idx_events_org_starts ON public.events (org_id, starts_at);
CREATE INDEX idx_shares_org_created ON public.shares (org_id, created_at DESC);


-- =============================================================================
-- RLS
--   既存規約に合わせる: 参照は所属org、書き込みは can_edit_org()
-- =============================================================================
ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attachments ENABLE ROW LEVEL SECURITY;

-- articles
CREATE POLICY "articles_select" ON public.articles
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "articles_insert" ON public.articles
  FOR INSERT TO authenticated
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "articles_update" ON public.articles
  FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id))
  WITH CHECK (public.can_edit_org(org_id));
-- 削除だけは owner/admin に限る。圭一郎さんは editor で運用し、
-- 「直したい」のつもりで記事を消してしまう事故を DB 側でも防ぐ
CREATE POLICY "articles_delete" ON public.articles
  FOR DELETE TO authenticated
  USING (public.has_org_role(org_id, 'owner') OR public.has_org_role(org_id, 'admin'));

-- article_reviews（履歴なので更新・削除はさせない）
CREATE POLICY "article_reviews_select" ON public.article_reviews
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "article_reviews_insert" ON public.article_reviews
  FOR INSERT TO authenticated
  WITH CHECK (
    public.can_edit_org(org_id)
    AND reviewer_user_id = (SELECT auth.uid())
  );

-- ideas
CREATE POLICY "ideas_select" ON public.ideas
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "ideas_insert" ON public.ideas
  FOR INSERT TO authenticated
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "ideas_update" ON public.ideas
  FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id))
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "ideas_delete" ON public.ideas
  FOR DELETE TO authenticated
  USING (public.can_edit_org(org_id));

-- events
CREATE POLICY "events_select" ON public.events
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "events_insert" ON public.events
  FOR INSERT TO authenticated
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "events_update" ON public.events
  FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id))
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "events_delete" ON public.events
  FOR DELETE TO authenticated
  USING (public.can_edit_org(org_id));

-- shares
CREATE POLICY "shares_select" ON public.shares
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "shares_insert" ON public.shares
  FOR INSERT TO authenticated
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "shares_update" ON public.shares
  FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id))
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "shares_delete" ON public.shares
  FOR DELETE TO authenticated
  USING (public.can_edit_org(org_id));

-- attachments
CREATE POLICY "attachments_select" ON public.attachments
  FOR SELECT TO authenticated
  USING (org_id IN (SELECT public.get_user_org_ids()));
CREATE POLICY "attachments_insert" ON public.attachments
  FOR INSERT TO authenticated
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "attachments_update" ON public.attachments
  FOR UPDATE TO authenticated
  USING (public.can_edit_org(org_id))
  WITH CHECK (public.can_edit_org(org_id));
CREATE POLICY "attachments_delete" ON public.attachments
  FOR DELETE TO authenticated
  USING (public.can_edit_org(org_id));
