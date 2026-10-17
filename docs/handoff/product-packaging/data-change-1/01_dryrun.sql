-- ADR-1028 便2 DRY-RUN: 01_apply.sql と同じ中身。件数を表示してから必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';

-- 4-1. CARD を名簿に足す
INSERT INTO public.quantity_units (code, name, name_en, display_order, is_active)
SELECT 'CARD', 'カード', 'Card', 40, true
WHERE NOT EXISTS (SELECT 1 FROM public.quantity_units WHERE code = 'CARD');

-- 4-2. 古い列から写す
-- CASE の行（中は BOX）: boxes_per_case か case_weight_kg が有る商品。DRY-RUN の想定 146 行
INSERT INTO public.product_packagings
    (product_id, unit_id, contained_unit_id, contained_count, count_source, weight_kg, weight_source, updated_by)
SELECT p.id, uc.id,
       CASE WHEN p.boxes_per_case IS NOT NULL THEN ub.id END,
       p.boxes_per_case,
       CASE WHEN p.boxes_per_case IS NOT NULL THEN 'legacy' END,
       p.case_weight_kg,
       CASE WHEN p.case_weight_kg IS NOT NULL THEN 'legacy' END,
       'ADR-1028 data-change-1'
FROM public.products p
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'CASE') uc
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'BOX') ub
WHERE p.boxes_per_case IS NOT NULL OR p.case_weight_kg IS NOT NULL
ON CONFLICT (product_id, unit_id) DO NOTHING;

-- BOX の行（中は PACK）: packs_per_box か box_weight_kg が有る商品。DRY-RUN の想定 176 行
INSERT INTO public.product_packagings
    (product_id, unit_id, contained_unit_id, contained_count, count_source, weight_kg, weight_source, updated_by)
SELECT p.id, ub.id,
       CASE WHEN p.packs_per_box IS NOT NULL THEN up.id END,
       p.packs_per_box,
       CASE WHEN p.packs_per_box IS NOT NULL THEN 'legacy' END,
       p.box_weight_kg,
       CASE WHEN p.box_weight_kg IS NOT NULL THEN 'legacy' END,
       'ADR-1028 data-change-1'
FROM public.products p
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'BOX') ub
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'PACK') up
WHERE p.packs_per_box IS NOT NULL OR p.box_weight_kg IS NOT NULL
ON CONFLICT (product_id, unit_id) DO NOTHING;

-- 件数ガード: 違えば RAISE EXCEPTION（ON_ERROR_STOP で止まり、COMMIT に進まない）
DO $guard$
DECLARE
    n_card integer;
    n_case integer;
    n_box  integer;
BEGIN
    SELECT count(*) INTO n_card FROM public.quantity_units WHERE code = 'CARD';
    SELECT count(*) INTO n_case FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id
     WHERE u.code = 'CASE' AND x.updated_by = 'ADR-1028 data-change-1';
    SELECT count(*) INTO n_box  FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id
     WHERE u.code = 'BOX' AND x.updated_by = 'ADR-1028 data-change-1';
    IF n_card <> 1 THEN RAISE EXCEPTION 'CARD must be 1 but was %', n_card; END IF;
    IF n_case <> 146 THEN RAISE EXCEPTION 'CASE rows must be 146 but was %', n_case; END IF;
    IF n_box <> 176 THEN RAISE EXCEPTION 'BOX rows must be 176 but was %', n_box; END IF;
END
$guard$;

SELECT 'CARD' AS k, count(*) FROM public.quantity_units WHERE code = 'CARD'
UNION ALL SELECT 'CASE_ROWS', count(*) FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id WHERE u.code = 'CASE'
UNION ALL SELECT 'BOX_ROWS', count(*) FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id WHERE u.code = 'BOX'
UNION ALL SELECT 'ALL_ROWS', count(*) FROM public.product_packagings;
ROLLBACK;
SELECT 'DRYRUN_OK';
