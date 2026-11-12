-- ADR-1031 What 6 便2 事前確認（読むだけ）。設計 docs/handoff/single-set-category/design.md §8 便2。
-- 期待: PRECHECK_OK が 3 行。1つでも違えば 1/0 で失敗して止まる。
-- 前提: 便1（PR #5417）のコードが本番に出ていること（2026-11-12 05:36Z 配備済み）。
\set ON_ERROR_STOP on
-- 1. 区分の今の行（03_verify の ROW 行と突き合わせる基準）
SELECT 'ROW|' || id || '|' || code || '|' || display_name || '|' || kubun_type || '|' || is_active || '|' || coalesce(tenant_id::text, 'NULL')
  FROM public.tcg_product_categories ORDER BY id;
-- 2. code・kubun_type・display_name が今の行と重ならない（設計 §8 便2「01_precheck で重ならないことを確かめる」）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK category_absent 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories
 WHERE code = 'PC_SINGLE_SET' OR kubun_type = 'シングルセット系' OR display_name = 'Single set';
-- 3. シングルセット系の商品が 0 件（K3。付け替えは便3）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK single_set_products 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.kubun_type = 'シングルセット系';
-- 4. 区分ごとの商品数（03_verify と同じ数になることを手で突き合わせる）
SELECT 'COUNT|' || coalesce(c.code, 'NULL') || '|' || count(*)
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 GROUP BY c.code ORDER BY 1;
-- 5. 前例の区分 PC_SET が有効（便3 の付け替え元。ここでは変えない）
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK pc_set_active 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories WHERE code = 'PC_SET' AND kubun_type = 'セット系' AND is_active;
