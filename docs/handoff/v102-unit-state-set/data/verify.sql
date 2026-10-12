-- 便SU の verify（読み取り）。CATEGORY|PC_SET|セット系|true、PRODUCT|PM0297|PC_SET、SET_PRODUCTS|1 が出ること。
SELECT 'CATEGORY|' || code || '|' || kubun_type || '|' || is_active FROM public.tcg_product_categories WHERE code = 'PC_SET';
SELECT 'PRODUCT|' || p.product_code || '|' || c.code FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id WHERE p.product_code = 'PM0297';
SELECT 'SET_PRODUCTS|' || count(*) FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id WHERE c.code = 'PC_SET';
SELECT 'VERIFY_DONE';
