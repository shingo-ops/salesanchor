-- ADR-1031 What 6 便3 手順 2 適用。13 商品の区分をセット系 → シングルセット系へ付け替える（記録 SQL。migration には書かない＝ADR-1007）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : -v end=ROLLBACK   （件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : -v end=COMMIT     （DRY-RUN が全部 OK だった後だけ）
-- 前後の区分は audit_log に 1 行（印 single-set-bin3-20261112。画面で商品を直したときと同じ表）で残し、BEFORE 行・AFTER 行として出力にも出す。
-- 件数が違えば 1/0 で失敗し、COMMIT に進まない。audit_log の書き方の前例: docs/handoff/revival-guard/data/02_apply.sql。
-- 前例: ADR-1035 便2（docs/handoff/condition-unit-booklet/data/bin2/02_apply.sql）の商品の付け替え。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;
SET LOCAL lock_timeout = '1s';

-- 1. 書く前の区分
SELECT 'BEFORE|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;

-- 2. 記録（書く前の区分と付け替え先）。今セット系の 13 行がそろっていなければ 1 行も入らず失敗
WITH aud AS (
    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    SELECT 'products', gen_random_uuid(), 'UPDATE', 'claude-opus (single-set-bin3-20261112; PO 2026-11-12)',
           jsonb_agg(jsonb_build_object('id', p.id, 'product_category_id', p.product_category_id, 'code', c.code) ORDER BY p.id)::text,
           jsonb_build_object('merge_id', 'single-set-bin3-20261112',
                              'to_code', 'PC_SINGLE_SET',
                              'to_id', (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SINGLE_SET'),
                              'product_ids', jsonb_agg(p.id ORDER BY p.id))::text
      FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
     WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
       AND c.code = 'PC_SET'
    HAVING count(*) = 13
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'AUDIT_INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM aud;

-- 3. 付け替え（今セット系の行だけ。13 行でなければ失敗）
WITH upd AS (
    UPDATE public.products
       SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SINGLE_SET' AND is_active)
     WHERE id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
       AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 13 THEN 'UPDATED products|13' ELSE (1 / (count(*) - count(*)))::text END FROM upd;

-- 4. 書いた後の区分
SELECT 'AFTER|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;

-- 5. 適用後の確認（件数が違えば失敗）
SELECT CASE WHEN count(*) = 13 THEN 'CHECK_OK targets_single_set 13' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
   AND c.code = 'PC_SINGLE_SET' AND c.kubun_type = 'シングルセット系';
SELECT CASE WHEN count(*) = 13 THEN 'CHECK_OK single_set_products 13' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SINGLE_SET';
SELECT CASE WHEN count(*) = 7 THEN 'CHECK_OK pc_set_products 7' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SET';
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK audit 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.audit_log
 WHERE table_name = 'products' AND new_values LIKE '%single-set-bin3-20261112%' AND changed_by LIKE 'claude-opus (single-set-bin3-20261112;%';

:end;
SELECT 'APPLY_END';
