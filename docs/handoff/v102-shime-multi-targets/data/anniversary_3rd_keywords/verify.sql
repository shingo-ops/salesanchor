-- 登録後の確認（読み取りのみ）
-- 期待: 1 は検索 3 語・除外 16 語、2 は 2957 と 983（登録前 2956 + 1、979 + 4）
-- 1. 読む側（backend/app/services/extraction_shadow_svc.py:86-106 load_product_entries）と同じ並び順
SELECT p.id,
       (SELECT array_agg(k.keyword ORDER BY k.position, k.keyword)
        FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_keywords,
       (SELECT array_agg(k.keyword ORDER BY k.position, k.keyword)
        FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_keywords
FROM public.products p
WHERE p.id = 440574 AND p.is_active = TRUE;

-- 2. 全件数
SELECT (SELECT count(*) FROM public.product_search_keywords) AS search_n,
       (SELECT count(*) FROM public.product_exclude_keywords) AS exclude_n;
