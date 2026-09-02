-- 「AI が直した。圭一郎さんの確認まち」という状態を足す。
--
-- 2026-09-02: 圭一郎さんの修正依頼を AI が適用する流れを作るにあたり、
-- 既存の needs_check（＝自動検証が問題を見つけた）を転用すると意味が混ざるため、
-- 専用の状態を設ける。圭一郎さんの画面には「直しました」と出す。

ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_status_check;

ALTER TABLE public.articles ADD CONSTRAINT articles_status_check
  CHECK (status IN (
    'ai_draft',    -- AI下書き
    'needs_check', -- 要確認あり（自動検証がひっかかった）
    'staff_ok',    -- 康二郎OK（一次承認）
    'needs_fix',   -- 圭一郎さんから直しの依頼が来ている
    'revised',     -- AI が直した。圭一郎さんの確認まち
    'approved',    -- 圭一郎OK
    'scheduled',   -- 投稿予約
    'published'    -- 投稿済
  ));

-- revised のときは、直す前（body_ai）と直した後（body_final）を並べて見せる。
-- そのため body_final が入っていることを保証する
ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_revised_requires_body;
ALTER TABLE public.articles ADD CONSTRAINT articles_revised_requires_body
  CHECK (status <> 'revised' OR body_final IS NOT NULL);

COMMENT ON COLUMN public.articles.body_final IS
  'AI が修正依頼を反映した本文。圭一郎さんが承認したらこれを投稿する。'
  'シートの「修正版」列は指示文を書く欄として使われていたため、ここには入れない';
