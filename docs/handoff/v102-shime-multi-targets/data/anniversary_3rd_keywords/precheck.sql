-- 登録前の状態確認（読み取りのみ）
-- 期待: 1 は 2 行（3rd anniversary set / 3rd anniversary、position 0・1）、2 は 12 行（position 1〜12）
--       3 は 0 行、4 は 0 行、5 は 2956 と 979、6 は is_active = t
-- 1. 440574 の今の検索ワード
SELECT product_id, position, keyword FROM public.product_search_keywords
WHERE product_id = 440574 ORDER BY position;

-- 2. 440574 の今の除外ワード
SELECT product_id, position, keyword FROM public.product_exclude_keywords
WHERE product_id = 440574 ORDER BY position;

-- 3. 足す検索ワードが既にどこかにあるか
SELECT product_id, keyword FROM public.product_search_keywords
WHERE keyword = '3rd アニバーサリー';

-- 4. 足す除外ワードが 440574 に既にあるか
SELECT product_id, keyword FROM public.product_exclude_keywords
WHERE product_id = 440574 AND keyword IN ('イングリッシュ', 'チャイナ', '中国', '英語');

-- 5. 全件数
SELECT (SELECT count(*) FROM public.product_search_keywords) AS search_n,
       (SELECT count(*) FROM public.product_exclude_keywords) AS exclude_n;

-- 6. 440574 が有効か
SELECT id, product_code, is_active, work_id FROM public.products WHERE id = 440574;
