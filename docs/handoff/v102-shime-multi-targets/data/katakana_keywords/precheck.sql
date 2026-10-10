-- 登録前の状態確認（読み取りのみ）
-- 期待: 1 は 4 行（440406: 30th CELEBRATION / 30周年 CELEBRATION、125081: 30th FUTURISTIC / 30周年 FUTURISTIC、position 0・1）
--       2 は 0 行、3 は 2954、4 は 2 行とも is_active = t
-- 1. 対象2商品の今の検索ワード
SELECT product_id, position, keyword
FROM public.product_search_keywords
WHERE product_id IN (440406, 125081)
ORDER BY product_id, position;

-- 2. 足す2語が既にどこかの商品にあるか
SELECT product_id, keyword
FROM public.product_search_keywords
WHERE keyword IN ('30th セレブレーション', '30th フューチャリスティック');

-- 3. 全件数
SELECT count(*) AS n FROM public.product_search_keywords;

-- 4. 対象2商品が有効か
SELECT id, product_code, is_active, work_id
FROM public.products
WHERE id IN (440406, 125081)
ORDER BY id;
