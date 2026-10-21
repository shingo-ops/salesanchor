-- ADR-1031 S4 戻し。本番での実行は Opus。8 行を無効にし、3 商品を区分 2 に戻す（区分の行は残す）。続けて対象 job を再解析する。
\set ON_ERROR_STOP on
BEGIN;
WITH u AS (
    UPDATE public.line_conditions SET is_active = FALSE
     WHERE code IN ('CN0015','CN0016','CN0017','CN0018','CN0019','CN0020','CN0021','CN0022') AND is_active
    RETURNING id
)
SELECT CASE WHEN count(*) = 8 THEN 'ROLLBACK conditions|8' ELSE (1 / (count(*) - count(*)))::text END FROM u;
WITH u AS (
    UPDATE public.products SET product_category_id = 2
     WHERE id IN (440525, 466083, 466077)
       AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_PROMO_PACK')
    RETURNING id
)
SELECT CASE WHEN count(*) = 3 THEN 'ROLLBACK products|3' ELSE (1 / (count(*) - count(*)))::text END FROM u;
COMMIT;
SELECT 'ROLLBACK_DONE';
