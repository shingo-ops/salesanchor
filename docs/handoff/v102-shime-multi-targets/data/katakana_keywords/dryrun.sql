-- DRY-RUN: 入れて確認して ROLLBACK（何も残らない）。期待: INSERT 0 2、対象2商品が各3行（position 2 に新しい語）
BEGIN;

INSERT INTO public.product_search_keywords (product_id, position, keyword)
SELECT v.product_id, v.position, v.keyword
FROM (VALUES (440406, 2, '30th セレブレーション'),
             (125081, 2, '30th フューチャリスティック')) AS v(product_id, position, keyword)
WHERE NOT EXISTS (
    SELECT 1 FROM public.product_search_keywords k
    WHERE k.product_id = v.product_id AND k.keyword = v.keyword
);

SELECT product_id, position, keyword
FROM public.product_search_keywords
WHERE product_id IN (440406, 125081)
ORDER BY product_id, position;

ROLLBACK;
