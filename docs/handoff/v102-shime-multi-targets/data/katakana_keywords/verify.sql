-- 登録後の確認（読み取りのみ）
-- 期待: 1 は 6 行（各商品 position 0・1・2）、2 は 2956（登録前 2954 + 2）
-- 1. 読む側（backend/app/services/extraction_shadow_svc.py:86-106 load_product_entries）と同じ並び順で、対象2商品の検索ワード
SELECT p.id,
       (SELECT array_agg(k.keyword ORDER BY k.position, k.keyword)
        FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_keywords
FROM public.products p
WHERE p.id IN (440406, 125081) AND p.is_active = TRUE
ORDER BY p.id;

SELECT product_id, position, keyword
FROM public.product_search_keywords
WHERE product_id IN (440406, 125081)
ORDER BY product_id, position;

-- 2. 全件数
SELECT count(*) AS n FROM public.product_search_keywords;
