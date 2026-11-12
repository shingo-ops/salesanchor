-- ADR-1031 What 6 便3 手順 2 事前確認（読むだけ）。設計 docs/handoff/single-set-category/design.md §5「### 便3」。
-- 期待: PRECHECK_OK が 4 行。1つでも違えば 1/0 で失敗して止まる。
-- 前提: 便2 で区分 PC_SINGLE_SET が本番に入っていること（2026-11-12 19:58 JST）。
-- 対象: PO が 2026-11-12「1」で決めた 13 商品（設計 §5 便3 手順 1）。
\set ON_ERROR_STOP on
-- 1. 13 商品の今の区分（02 の BEFORE 行・03 の ROW 行と突き合わせる基準）
SELECT 'ROW|' || p.id || '|' || coalesce(p.product_category_id::text, 'NULL') || '|' || coalesce(c.code, 'NULL') || '|' || p.is_active || '|' || coalesce(p.tenant_id::text, 'NULL')
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
 ORDER BY p.id;
-- 2. 13 商品がすべてあり、すべてセット系（PC_SET）
SELECT CASE WHEN count(*) = 13 THEN 'PRECHECK_OK targets_in_pc_set 13' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
   AND c.code = 'PC_SET' AND c.kubun_type = 'セット系';
-- 3. 付け替え先の区分が 1 行だけ有効（便2 の結果）
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK single_set_category_active 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories
 WHERE code = 'PC_SINGLE_SET' AND kubun_type = 'シングルセット系' AND is_active AND tenant_id IS NULL;
-- 4. シングルセット系の商品が 0 件（まだ付け替えていない）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK single_set_products 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SINGLE_SET';
-- 5. セット系の商品が 20 件（付け替えの後は 7 件になる）
SELECT CASE WHEN count(*) = 20 THEN 'PRECHECK_OK pc_set_products 20' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.code = 'PC_SET';
-- 6. 区分ごとの商品数（03_verify と手で突き合わせる）
SELECT 'COUNT|' || coalesce(c.code, 'NULL') || '|' || count(*)
  FROM public.products p LEFT JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 GROUP BY c.code ORDER BY 1;
