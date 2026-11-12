-- ADR-1031 What 6 便2 確認（読むだけ）。COMMIT の後に流す（K4）。全部 VERIFY_OK なら期待どおり。
-- ROW 行・COUNT 行は 01_precheck.sql と同じ書式。既存の 6 行と区分ごとの商品数が前後で同じであることを手で突き合わせる。
\set ON_ERROR_STOP on
SELECT 'ROW|' || id || '|' || code || '|' || display_name || '|' || kubun_type || '|' || is_active || '|' || coalesce(tenant_id::text, 'NULL')
  FROM public.tcg_product_categories ORDER BY id;
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK category 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories
 WHERE code = 'PC_SINGLE_SET' AND display_name = 'Single set' AND kubun_type = 'シングルセット系' AND is_active AND tenant_id IS NULL;
SELECT CASE WHEN count(*) = 0 THEN 'VERIFY_OK single_set_products 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.kubun_type = 'シングルセット系';
SELECT 'COUNT|' || coalesce(c.code, 'NULL') || '|' || count(*)
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 GROUP BY c.code ORDER BY 1;
