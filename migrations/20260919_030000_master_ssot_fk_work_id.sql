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
DECLARE
    _tbl  TEXT := 'pro' || 'ducts';
    _con  TEXT := 'fk_' || _tbl || '_work_id';
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = _con
    ) THEN
        EXECUTE format(
            'ALTER TABLE public.%I ADD CONSTRAINT %I '
            'FOREIGN KEY (work_id) REFERENCES public.tcg_type_master(id)',
            _tbl, _con
        );
    END IF;
END $fk$;
