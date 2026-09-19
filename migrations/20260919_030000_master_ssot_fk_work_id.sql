-- ============================================================================
-- Migration 20260919_030000: products.work_id → tcg_type_master FK制約
--
-- 背景:
--   Phase 1 で products.work_id を UUID → INTEGER に変更し、
--   tcg_type_master.id を参照する値にデータ張替え済み。
--   FK制約を追加して参照整合性を保証する。
--
-- 冪等性:
--   pg_constraint で制約の存在を確認してからADD CONSTRAINT
-- ============================================================================

DO $fk$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_products_work_id'
    ) THEN
        ALTER TABLE public.products
        ADD CONSTRAINT fk_products_work_id
        FOREIGN KEY (work_id) REFERENCES public.tcg_type_master(id);
    END IF;
END $fk$;
