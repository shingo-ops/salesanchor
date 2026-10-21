-- ADR-1030: products.tcg_type を取り除く（作品の正本は products.work_id）
-- 便1 でアプリは列を読まない（docs/handoff/inventory-tab-by-work-id/design.md §3）
-- 依存は FK・索引・ai_ro ビューのみ（recon §h）。ai_ro ビューは run_all_migrations.sh の先頭で外れ最後に作り直される
-- 冪等: IF EXISTS。値は書かない（ADR-1007）
ALTER TABLE public.products DROP CONSTRAINT IF EXISTS fk_products_tcg_type;
DROP INDEX IF EXISTS public.idx_public_products_tcg_type;
ALTER TABLE public.products DROP COLUMN IF EXISTS tcg_type;
