-- ADR-1031 What 6 便3 手順 2 の戻し（設計 §9「商品を元の区分に戻し」）。13 商品をシングルセット系 → セット系へ戻す。
-- 13 行でなければ 1/0 で止まる（取引ごと取り消し）。解析の行は戻らないので、戻した後は設計 §9 のとおり書く前の全行を見て対象の job を再解析する。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '1s';
SELECT 'BEFORE|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;
WITH upd AS (
    UPDATE public.products
       SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SET' AND is_active)
     WHERE id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
       AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SINGLE_SET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 13 THEN 'ROLLBACK products|13' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
SELECT CASE WHEN count(*) = 0 THEN 'ROLLBACK_CHECK_OK single_set_products 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SINGLE_SET';
SELECT CASE WHEN count(*) = 20 THEN 'ROLLBACK_CHECK_OK pc_set_products 20' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SET';
COMMIT;
SELECT 'ROLLBACK_DONE';
