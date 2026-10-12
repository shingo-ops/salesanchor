-- 便SU 分類セット系の投入 precheck（読み取り）。CODE_DUP|0、KUBUN_DUP|0、PRODUCT|1|PM0297|1、UNIT_SET|1 が出ること。
SELECT 'CODE_DUP|' || count(*) FROM public.tcg_product_categories WHERE code = 'PC_SET';
SELECT 'KUBUN_DUP|' || count(*) FROM public.tcg_product_categories WHERE kubun_type = 'セット系';
SELECT 'PRODUCT|' || count(*) || '|' || coalesce(max(product_code), 'NULL') || '|' || coalesce(max(product_category_id)::text, 'NULL') FROM public.products WHERE product_code = 'PM0297';
SELECT 'UNIT_SET|' || count(*) FROM public.line_units WHERE code = 'UN0005' AND is_active = TRUE;
SELECT 'PRECHECK_DONE';
