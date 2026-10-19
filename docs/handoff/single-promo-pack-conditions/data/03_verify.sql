-- ADR-1031 S3 確認（読むだけ）。適用後に流す。全部 VERIFY_OK なら期待どおり。
\set ON_ERROR_STOP on
SELECT CASE WHEN count(*) = 8 THEN 'VERIFY_OK conditions 8' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE code IN ('CN0015','CN0016','CN0017','CN0018','CN0019','CN0020','CN0021','CN0022')
   AND is_active AND effect = 'OUTPUT' AND unit_id IS NULL AND value_group IN ('single','promo_pack')
   AND ((value_group = 'single' AND app_kubun = 'シングル系') OR (value_group = 'promo_pack' AND app_kubun = 'プロモパック系'));
SELECT CASE WHEN count(*) = 5 THEN 'VERIFY_OK single 5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single' AND is_active;
SELECT CASE WHEN count(*) = 3 THEN 'VERIFY_OK promo_pack 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'promo_pack' AND is_active;
SELECT CASE WHEN count(*) = 16 THEN 'VERIFY_OK existing_unchanged 16' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code NOT IN ('CN0015','CN0016','CN0017','CN0018','CN0019','CN0020','CN0021','CN0022');
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK category 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories WHERE code = 'PC_PROMO_PACK' AND kubun_type = 'プロモパック系' AND is_active;
SELECT CASE WHEN count(*) = 3 THEN 'VERIFY_OK products 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (440525, 466083, 466077) AND c.kubun_type = 'プロモパック系';
SELECT CASE WHEN count(*) = 0 THEN 'VERIFY_OK other_products_untouched 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.kubun_type = 'プロモパック系' AND p.id NOT IN (440525, 466083, 466077);
