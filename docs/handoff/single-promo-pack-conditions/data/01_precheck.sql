-- ADR-1031 S1 事前確認（読むだけ）。本番への実行は Opus（担当は実行しない）。
-- 期待: 全部 PRECHECK_OK。1つでも違えば止まる（1/0 で失敗させる）。
\set ON_ERROR_STOP on
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK code_unused 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code IN ('CN0015','CN0016','CN0017','CN0018','CN0019','CN0020','CN0021','CN0022');
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK canonical_unused 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE canonical IN ('Single','未開封','開封済み','PSA9','PSA8','PSA7以下','PSA10');
SELECT CASE WHEN count(*) = 16 THEN 'PRECHECK_OK conditions 16' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions;
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK category_absent 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories WHERE code = 'PC_PROMO_PACK' OR kubun_type = 'プロモパック系';
SELECT CASE WHEN count(*) = 3 THEN 'PRECHECK_OK products_in_category_2 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products WHERE id IN (440525, 466083, 466077) AND product_category_id = 2;
