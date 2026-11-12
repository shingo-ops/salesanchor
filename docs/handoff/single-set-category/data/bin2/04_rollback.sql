-- ADR-1031 What 6 便2 戻し（設計 §9「区分の行を is_active=false にする（商品が付いていない間だけ）」）。
-- 商品が 1 件でも付いていれば 1/0 で止まる（便3 の後は便3 の戻しを先に流す）。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '1s';
SELECT CASE WHEN count(*) = 0 THEN 'ROLLBACK_PRECHECK_OK single_set_products 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SINGLE_SET';
WITH u AS (
    UPDATE public.tcg_product_categories SET is_active = false, updated_at = NOW()
     WHERE code = 'PC_SINGLE_SET' AND is_active RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK category|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
COMMIT;
SELECT 'ROLLBACK_DONE';
