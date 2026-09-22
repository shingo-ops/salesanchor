-- ============================================================================
-- Migration 20260923_020000: line_import_devices.tcg_schema を
--                            'tenant_004' → 'public' に更新
--
-- 経緯:
--   fix-tcg-schema-wiring ブランチでコード側の TCG_SCHEMA デフォルトを
--   "tenant_004" → "public" に変更。
--   既存デバイスレコードの tcg_schema カラムも合わせて更新する。
--
-- 冪等性:
--   WHERE tcg_schema = 'tenant_004' のため再実行しても更新行ゼロで安全。
--
-- 作成日: 2026-09-23
-- ============================================================================

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'line_import_devices') THEN
        UPDATE public.line_import_devices
        SET tcg_schema = 'public'
        WHERE tcg_schema = 'tenant_004';

        GET DIAGNOSTICS updated_count = ROW_COUNT;
        RAISE NOTICE 'migration 20260923_020000: line_import_devices.tcg_schema を % 行更新 (tenant_004 → public)',
            updated_count;
    ELSE
        RAISE NOTICE 'migration 20260923_020000: public.line_import_devices 不在 — スキップ（CI環境）';
    END IF;
END $$;

-- ============================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- UPDATE public.line_import_devices
-- SET tcg_schema = 'tenant_004'
-- WHERE tcg_schema = 'public';
-- ============================================================================
