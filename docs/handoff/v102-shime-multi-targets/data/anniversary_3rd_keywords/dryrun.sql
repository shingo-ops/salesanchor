-- DRY-RUN: 入れて確認して ROLLBACK（何も残らない）。期待: INSERT 0 1 と INSERT 0 4、検索 3 行・除外 16 行
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

SELECT product_id, position, keyword FROM public.product_search_keywords
WHERE product_id = 440574 ORDER BY position;
SELECT product_id, position, keyword FROM public.product_exclude_keywords
WHERE product_id = 440574 ORDER BY position;

ROLLBACK;
