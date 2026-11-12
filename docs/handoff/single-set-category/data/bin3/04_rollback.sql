-- ADR-1031 What 6 便3 手順 2 の戻し（設計 §9「商品を元の区分に戻し」）。13 商品をシングルセット系 → セット系へ戻す。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : -v end=ROLLBACK   （件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : -v end=COMMIT     （DRY-RUN が全部 OK だった後だけ）
-- 13 行でなければ 1/0 で止まる（取引ごと取り消し）。戻したことも audit_log に 1 行残す（印 single-set-bin3-20261112-rollback）。
-- 13 商品のうちどれかが付け替えの後に画面で別の区分に変わっていると全体が止まる。そのときは BEFORE 行で外れた商品を見て、PO に聞く。
-- 解析の行は戻らないので、戻した後は設計 §9 のとおり書く前の全行を見て対象の job を再解析する。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;
SET LOCAL lock_timeout = '1s';
SELECT 'BEFORE|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;
-- 付け替えの記録が 1 行あること（無ければ戻す相手が無い）
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK_CHECK_OK audit_found 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.audit_log
 WHERE table_name = 'products' AND new_values LIKE '%single-set-bin3-20261112%' AND changed_by LIKE 'claude-opus (single-set-bin3-20261112;%';
WITH aud AS (
    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    SELECT 'products', gen_random_uuid(), 'UPDATE', 'claude-opus (single-set-bin3-20261112-rollback)',
           jsonb_agg(jsonb_build_object('id', p.id, 'product_category_id', p.product_category_id, 'code', c.code) ORDER BY p.id)::text,
           jsonb_build_object('merge_id', 'single-set-bin3-20261112-rollback', 'to_code', 'PC_SET',
                              'product_ids', jsonb_agg(p.id ORDER BY p.id))::text
      FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
     WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
       AND c.code = 'PC_SINGLE_SET'
    HAVING count(*) = 13
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK_AUDIT|1' ELSE (1 / (count(*) - count(*)))::text END FROM aud;
WITH upd AS (
    UPDATE public.products
       SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SET' AND is_active)
     WHERE id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
       AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SINGLE_SET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 13 THEN 'ROLLBACK products|13' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
SELECT 'AFTER|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;
SELECT CASE WHEN count(*) = 0 THEN 'ROLLBACK_CHECK_OK single_set_products 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SINGLE_SET';
SELECT CASE WHEN count(*) = 20 THEN 'ROLLBACK_CHECK_OK pc_set_products 20' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SET';
:end;
SELECT 'ROLLBACK_END';
