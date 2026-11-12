-- ADR-1031 What 6 便3 手順 2 確認（読むだけ）。COMMIT の後に流す。全部 VERIFY_OK なら期待どおり。
-- ROW 行・COUNT 行は 01_precheck.sql と同じ書式。13 商品だけがセット系 → シングルセット系に動き、ほかの区分の数が変わっていないことを手で突き合わせる。
\set ON_ERROR_STOP on
SELECT 'ROW|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL') || '|' || p.is_active || '|' || coalesce(p.tenant_id::text, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;
SELECT CASE WHEN count(*) = 13 THEN 'VERIFY_OK targets_single_set 13' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
   AND c.code = 'PC_SINGLE_SET' AND c.kubun_type = 'シングルセット系';
SELECT CASE WHEN count(*) = 13 THEN 'VERIFY_OK single_set_products 13' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SINGLE_SET';
SELECT CASE WHEN count(*) = 7 THEN 'VERIFY_OK pc_set_products 7' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SET';
SELECT 'COUNT|' || coalesce(c.code, 'NULL') || '|' || count(*)
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 GROUP BY c.code ORDER BY 1;
