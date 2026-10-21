-- ADR-1035 便2 確認（読むだけ）。COMMIT の後に流す。全部 VERIFY_OK なら期待どおり。
-- ROW 行は 01_precheck.sql の ROW 行と同じ書式。実行者が前後で既存の行が同じであることを手で突き合わせる。
\set ON_ERROR_STOP on
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK with_booklet 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE canonical = 'With booklet' AND value_group = 'booklet' AND app_kubun = 'ブックレット系'
   AND match_type = 'KEYWORD' AND priority = 10 AND value_rank = 1 AND unit_id = 17 AND effect = 'OUTPUT' AND is_active;
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK without_booklet 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE canonical = 'Without booklet' AND value_group = 'booklet' AND app_kubun = 'ブックレット系'
   AND match_type = 'REGEX' AND priority = 2 AND value_rank = 2 AND unit_id IS NULL AND effect = 'OUTPUT' AND is_active;
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK category 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories WHERE code = 'PC_BOOKLET' AND display_name = 'Booklet' AND kubun_type = 'ブックレット系' AND is_active;
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK product_440415 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id = 440415 AND c.code = 'PC_BOOKLET';
