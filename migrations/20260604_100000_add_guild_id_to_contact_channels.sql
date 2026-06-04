-- SA-05 C-3: contact_contact_channels に guild_id を追加
-- Discord guild_id を担当者チャンネルレベルで保持する
--
-- 設計:
--   - 全テナントスキーマ（nspname LIKE 'tenant_%'）を pg_namespace ループで走査
--   - contact_contact_channels テーブルが存在するスキーマのみ ALTER TABLE
--   - ADD COLUMN IF NOT EXISTS で冪等（再実行 no-op）
--   - NULL 許可・DEFAULT なし（既存行への影響なし）
--
-- 冪等性:
--   - ADD COLUMN IF NOT EXISTS
--   - テーブル存在確認で早期スキップ
--
-- additive-only: 列追加のみ。削除・型変更なし。
--
-- 作成日: 2026-06-04

DO $$
DECLARE
    schema_record RECORD;
    applied_count INTEGER := 0;
    skipped_no_table INTEGER := 0;
BEGIN
    FOR schema_record IN
        SELECT nspname AS schema_name FROM pg_namespace
        WHERE nspname LIKE 'tenant_%' ORDER BY nspname
    LOOP
        -- contact_contact_channels テーブルが存在する場合のみ ALTER
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_record.schema_name
            AND table_name = 'contact_contact_channels'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.contact_contact_channels ADD COLUMN IF NOT EXISTS guild_id VARCHAR(50)',
                schema_record.schema_name
            );
            applied_count := applied_count + 1;
            RAISE NOTICE 'migration 20260604_100000: %.contact_contact_channels に guild_id を追加', schema_record.schema_name;
        ELSE
            skipped_no_table := skipped_no_table + 1;
        END IF;
    END LOOP;

    RAISE NOTICE
        'migration 20260604_100000: 完了。適用 % テーブル、未存在スキップ % スキーマ',
        applied_count, skipped_no_table;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%'
--     LOOP
--         IF EXISTS (
--             SELECT 1 FROM information_schema.tables
--             WHERE table_schema = r.nspname AND table_name = 'contact_contact_channels'
--         ) THEN
--             EXECUTE format(
--                 'ALTER TABLE %I.contact_contact_channels DROP COLUMN IF EXISTS guild_id',
--                 r.nspname
--             );
--         END IF;
--     END LOOP;
-- END $$;
-- =====================================================================
