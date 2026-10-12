-- 便SU の戻し: 戻すときだけ使う。行は消さない。
-- 1. PM0297 の分類を PC_BOX（code で引く）に戻す。 2. PC_SET の行を is_active = false にする。
\set ON_ERROR_STOP on
BEGIN;
WITH upd AS (
    UPDATE public.products SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_BOX')
     WHERE product_code = 'PM0297' AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'RESTORED|1' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
WITH off AS (
    UPDATE public.tcg_product_categories SET is_active = FALSE WHERE code = 'PC_SET' AND is_active = TRUE RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'DEACTIVATED|1' ELSE (1 / (count(*) - count(*)))::text END FROM off;
COMMIT;
SELECT 'ROLLBACK_DONE';
