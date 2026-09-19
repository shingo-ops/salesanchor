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
    _ref_exists BOOLEAN;
BEGIN
    -- tcg_type_master が存在するか確認（CI テスト環境では未作成の場合がある）
    SELECT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'tcg_type_master'
    ) INTO _ref_exists;

    IF _ref_exists AND NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = _con
    ) THEN
        EXECUTE format(
            'ALTER TABLE public.%I ADD CONSTRAINT %I '
            'FOREIGN KEY (work_id) REFERENCES public.tcg_type_master(id)',
            _tbl, _con
        );
    END IF;
END $fk$;
