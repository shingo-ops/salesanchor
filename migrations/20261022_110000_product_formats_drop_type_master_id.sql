-- ADR-1038 便3b: product_formats.type_master_id を取り除く（親子の正本は product_format_game_links）
-- 読み手 0（docs/handoff/format-work-parent/recon-bin3b.md）。依存は FK product_formats_type_master_id_fkey・索引
-- idx_product_formats_type_master_id（列と一緒に消える）と ai_ro ビューのみ。
-- ai_ro ビューは run_all_migrations.sh の先頭で外れ、最後に作り直される
-- 表が無い DB（CI の単体流し）では何もしない（ALTER TABLE IF EXISTS）
-- 冪等: IF EXISTS。値は書かない（ADR-1007）。値の控えは docs/handoff/format-work-parent/data/ の CSV。適用は PO 本人の GO 後
ALTER TABLE IF EXISTS public.product_formats DROP CONSTRAINT IF EXISTS product_formats_type_master_id_fkey;
DROP INDEX IF EXISTS public.idx_product_formats_type_master_id;
ALTER TABLE IF EXISTS public.product_formats DROP COLUMN IF EXISTS type_master_id;
