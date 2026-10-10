-- COMMIT: カタカナの検索ワード2語を登録（PO 決定 2026-10-11 y）。dryrun.sql で INSERT 0 2 を確認してから実行
BEGIN;

INSERT INTO public.product_search_keywords (product_id, position, keyword)
SELECT v.product_id, v.position, v.keyword
FROM (VALUES (440406, 2, '30th セレブレーション'),
             (125081, 2, '30th フューチャリスティック')) AS v(product_id, position, keyword)
WHERE NOT EXISTS (
    SELECT 1 FROM public.product_search_keywords k
    WHERE k.product_id = v.product_id AND k.keyword = v.keyword
);

COMMIT;
