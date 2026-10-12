-- 便SU 分類セット系の投入 dryrun: 入れて検査して必ず ROLLBACK。件数が違えばゼロ除算で失敗する。id は書かない（identity）。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.tcg_product_categories (code, display_name, kubun_type, is_active, tenant_id)
    SELECT 'PC_SET', 'Set', 'セット系', TRUE, NULL
     WHERE NOT EXISTS (SELECT 1 FROM public.tcg_product_categories WHERE code = 'PC_SET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
WITH upd AS (
    UPDATE public.products SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SET')
     WHERE product_code = 'PM0297' AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_BOX')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED|1' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.product_code = 'PM0297' AND c.code = 'PC_SET' AND c.kubun_type = 'セット系' AND c.is_active = TRUE;
ROLLBACK;
SELECT 'DRYRUN_OK';
