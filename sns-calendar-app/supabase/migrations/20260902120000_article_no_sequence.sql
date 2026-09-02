-- 記事番号の採番を DB 側に移す。
--
-- 2026-09-02: シート上で ART-0040 が2件に重複していた。run_weekly_loop.py の
-- publish() が「シートの既存行数」から次の番号を決めていたため、途中の行を
-- 削除すると同じ番号が再発行されてしまう。行数は採番の根拠にならない。
--
-- シーケンスなら削除の影響を受けず、同時に走っても重複しない。

CREATE SEQUENCE IF NOT EXISTS public.article_no_seq;

-- 取り込み済みの最大値の次から始める。ART-0040-2 のような枝番は無視して
-- 数字4桁の部分だけを見る（枝番は重複対応で付けた一時的なもの）
SELECT setval(
  'public.article_no_seq',
  GREATEST(
    (SELECT COALESCE(MAX(SUBSTRING(article_no FROM '^ART-([0-9]{4})')::INT), 0)
     FROM public.articles),
    1
  )
);

CREATE OR REPLACE FUNCTION public.next_article_no()
RETURNS TEXT
LANGUAGE SQL
VOLATILE
AS $$
  SELECT 'ART-' || LPAD(nextval('public.article_no_seq')::TEXT, 4, '0');
$$;

COMMENT ON FUNCTION public.next_article_no() IS
  '記事番号を採番する。行数からではなくシーケンスから採るため、行を削除しても重複しない';

ALTER TABLE public.articles
  ALTER COLUMN article_no SET DEFAULT public.next_article_no();

-- 週次ループは service_role で書き込むが、将来 Route Handler から呼ぶ場合に備える
GRANT EXECUTE ON FUNCTION public.next_article_no() TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.article_no_seq TO authenticated, service_role;
