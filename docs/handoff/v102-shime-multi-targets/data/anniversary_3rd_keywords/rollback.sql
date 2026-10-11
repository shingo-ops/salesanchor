-- ROLLBACK: commit.sql で入れた 5 行だけを消す（product_id・keyword の組で絞る）
-- 期待: DELETE 1 と DELETE 4。違えば ROLLBACK して止める
BEGIN;

DELETE FROM public.product_search_keywords
WHERE product_id = 440574 AND keyword = '3rd アニバーサリー';

DELETE FROM public.product_exclude_keywords
WHERE product_id = 440574 AND keyword IN ('イングリッシュ', 'チャイナ', '中国', '英語');

-- 検索 2 行・除外 12 行に戻ったこと
SELECT count(*) AS search_rows FROM public.product_search_keywords WHERE product_id = 440574;
SELECT count(*) AS exclude_rows FROM public.product_exclude_keywords WHERE product_id = 440574;

-- 件数が合えば COMMIT; 合わなければ ROLLBACK;
COMMIT;
