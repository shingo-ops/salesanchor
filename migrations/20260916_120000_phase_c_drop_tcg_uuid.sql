-- ADR-1002 Phase C: Drop tcg_uuid column from public.products
-- 前提: Phase B 完了済み（全テナント FK → public.products(id)）
-- 参照元: なし（recon.md §3 で確認済み）

ALTER TABLE public.products DROP CONSTRAINT IF EXISTS uq_products_tcg_uuid;
DROP INDEX IF EXISTS idx_products_tcg_uuid;
ALTER TABLE public.products DROP COLUMN IF EXISTS tcg_uuid;
