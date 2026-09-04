-- AI が対応できなかった修正依頼を、圭一郎さんに聞き返せるようにする。
--
-- 2026-09-02 に発覚: apply_fixes.py が「どの画像にしますか」「URLを教えてください」と
-- 保留した3件（ART-0051/0053/0064）について、その理由がログにしか出ておらず、
-- 圭一郎さんの画面には「直しています。しばらくお待ちください」と出たままだった。
-- 待っても何も起きない。機能不足というより設計の穴。

ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_status_check;
ALTER TABLE public.articles ADD CONSTRAINT articles_status_check
  CHECK (status IN (
    'ai_draft',
    'needs_check',
    'staff_ok',
    'needs_fix',
    'needs_owner_input',  -- AI が直せず、圭一郎さんに聞き返している
    'revised',
    'approved',
    'scheduled',
    'published',
    'missed'
  ));

-- AI が「なぜ直せなかったか」を圭一郎さんの言葉で書く欄。
-- revision_note（字数超過などの申し送り）と同じ場所に表示する
COMMENT ON COLUMN public.articles.revision_note IS
  'AI から圭一郎さんへの申し送り。指示以外に手を入れた場合の確認や、'
  '直せなかった理由と聞き返し。承諾・返答があるまで投稿しない';

-- 聞き返している状態では、必ず理由が書かれていること
ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_owner_input_requires_note;
ALTER TABLE public.articles ADD CONSTRAINT articles_owner_input_requires_note
  CHECK (status <> 'needs_owner_input' OR revision_note IS NOT NULL);
