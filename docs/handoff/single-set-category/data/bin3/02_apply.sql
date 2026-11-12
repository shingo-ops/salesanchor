-- ADR-1031 What 6 便3 手順 2 適用。13 商品の区分をセット系 → シングルセット系へ付け替える（記録 SQL。migration には書かない＝ADR-1007）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : -v end=ROLLBACK   （件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : -v end=COMMIT     （DRY-RUN が全部 OK だった後だけ）
-- 前後の区分は BEFORE 行・AFTER 行として出力に残る（出力ファイルが記録）。件数が違えば 1/0 で失敗し、COMMIT に進まない。
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

-- 2. 付け替え（今セット系の行だけ。13 行でなければ失敗）
WITH upd AS (
    UPDATE public.products
       SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SINGLE_SET' AND is_active)
     WHERE id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
       AND product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_SET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 13 THEN 'UPDATED products|13' ELSE (1 / (count(*) - count(*)))::text END FROM upd;

-- 3. 書いた後の区分
SELECT 'AFTER|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;

-- 4. 適用後の確認（件数が違えば失敗）
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

:end;
SELECT 'APPLY_END';
