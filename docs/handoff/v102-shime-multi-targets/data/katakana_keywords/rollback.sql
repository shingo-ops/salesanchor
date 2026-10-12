-- ROLLBACK: commit.sql で入れた2行だけを消す（product_id・keyword の組で絞る）
-- 期待: DELETE 2。2 以外なら ROLLBACK して止める
BEGIN;

DELETE FROM public.product_search_keywords
WHERE (product_id, keyword) IN ((440406, '30th セレブレーション'),
                                (125081, '30th フューチャリスティック'));

-- 対象2商品が各2行（position 0・1）に戻ったこと
SELECT product_id, position, keyword
FROM public.product_search_keywords
WHERE product_id IN (440406, 125081)
ORDER BY product_id, position;

-- 件数が合えば COMMIT; 合わなければ ROLLBACK;
COMMIT;
