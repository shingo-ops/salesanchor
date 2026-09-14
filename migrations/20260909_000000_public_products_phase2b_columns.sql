-- Phase 2b column prerequisites: ensure public.products has the columns
-- that Phase 2b-modified migrations (20260910_*, 20260913_*) reference.
-- These columns are also added by 20260914_140000 (Phase 2a unification),
-- but that migration runs later in sort order. Using IF NOT EXISTS ensures
-- no conflict when 20260914 runs again.

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid          UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS division_id       UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS work_id           UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS manufacturer_id   UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS product_category_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS category_class    TEXT;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_active         BOOLEAN DEFAULT true;
