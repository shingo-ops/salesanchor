-- COMMIT: 3rd anniversary set（440574）に検索ワード1語・除外ワード4語を登録（PO 指示 2026-10-11）
-- dryrun.sql で INSERT 0 1 と INSERT 0 4 を確認してから実行
BEGIN;

INSERT INTO public.product_search_keywords (product_id, position, keyword)
SELECT 440574, 2, '3rd アニバーサリー'
WHERE NOT EXISTS (
    SELECT 1 FROM public.product_search_keywords k
    WHERE k.product_id = 440574 AND k.keyword = '3rd アニバーサリー'
);

INSERT INTO public.product_exclude_keywords (product_id, position, keyword)
SELECT 440574, v.position, v.keyword
FROM (VALUES (13, 'イングリッシュ'), (14, 'チャイナ'), (15, '中国'), (16, '英語')) AS v(position, keyword)
WHERE NOT EXISTS (
    SELECT 1 FROM public.product_exclude_keywords k
    WHERE k.product_id = 440574 AND k.keyword = v.keyword
);

COMMIT;
