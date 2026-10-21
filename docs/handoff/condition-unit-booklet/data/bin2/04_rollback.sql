-- ADR-1035 便2 戻し。本番での実行は Opus。新しい 2 行と区分の行を無効にし、440415 を区分 2 に戻す。続けて対象 job を再解析する。
-- CHECK 制約は広げたままでも害はない（design「戻し方」）。
\set ON_ERROR_STOP on
BEGIN;
WITH u AS (
    UPDATE public.line_conditions SET is_active = false, updated_at = NOW()
     WHERE value_group = 'booklet' AND app_kubun = 'ブックレット系' AND canonical IN ('With booklet', 'Without booklet') AND is_active
    RETURNING id
)
SELECT CASE WHEN count(*) = 2 THEN 'ROLLBACK conditions|2' ELSE (1 / (count(*) - count(*)))::text END FROM u;
WITH u AS (
    UPDATE public.products SET product_category_id = 2
     WHERE id = 440415 AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_BOOKLET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK product|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
WITH u AS (
    UPDATE public.tcg_product_categories SET is_active = false WHERE code = 'PC_BOOKLET' AND is_active RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK category|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
COMMIT;
SELECT 'ROLLBACK_DONE';
