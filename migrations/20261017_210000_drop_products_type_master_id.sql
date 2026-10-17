-- ADR-1026: products.type_master_id を取り除く（作品の正本は products.work_id）
-- 参照 0 件・依存は FK/索引/ai_ro ビューのみ（docs/handoff/drop-products-type-master-id/recon.md §2-3）
-- ai_ro ビューは run_all_migrations.sh の先頭で外れ、最後に作り直される
-- 冪等: IF EXISTS。値は書かない（ADR-1007）。適用は PO 本人の GO 後
ALTER TABLE public.products DROP CONSTRAINT IF EXISTS products_type_master_id_fkey;
DROP INDEX IF EXISTS public.idx_products_type_master_id;
ALTER TABLE public.products DROP COLUMN IF EXISTS type_master_id;
