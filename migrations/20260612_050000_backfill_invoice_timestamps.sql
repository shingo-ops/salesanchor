-- ADR-136 前提: paid_at / voided_at バックフィル
-- 背景:
--   アプリ経由の遷移は invoices.py / integrations.py で常に paid_at = NOW() を
--   セットしているが、直接 DB INSERT されたテストデータ・初期データには NULL が残る。
--   本 migration はその NULL を updated_at で近似補完する（updated_at も NULL の場合は
--   created_at を使用）。updated_at はアプリ更新時のタイムスタンプであり厳密ではないが
--   アーカイブ目的では十分な精度を持つ（コメント: 近似値・実際の入金日時とは異なる場合あり）。
--
-- 冪等性: paid_at IS NULL / voided_at IS NULL の行のみ対象。再実行で 0 件。
--
-- 実行順: 20260612_100000_fix_company_stats_ssot.sql（view 変更）より前に実行すること。

DO $$
DECLARE
    schema_rec RECORD;
    paid_updated   INTEGER;
    voided_updated INTEGER;
    total_paid     INTEGER := 0;
    total_voided   INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- invoices テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'invoices'
        ) THEN
            CONTINUE;
        END IF;

        -- paid_at バックフィル（status='paid' かつ paid_at IS NULL）
        EXECUTE format($q$
            UPDATE %I.invoices
            SET paid_at = COALESCE(updated_at, created_at)
            WHERE status = 'paid'
              AND paid_at IS NULL
        $q$, schema_rec.nspname);
        GET DIAGNOSTICS paid_updated = ROW_COUNT;
        total_paid := total_paid + paid_updated;

        -- voided_at バックフィル（status='voided' かつ voided_at IS NULL）
        EXECUTE format($q$
            UPDATE %I.invoices
            SET voided_at = COALESCE(updated_at, created_at)
            WHERE status = 'voided'
              AND voided_at IS NULL
        $q$, schema_rec.nspname);
        GET DIAGNOSTICS voided_updated = ROW_COUNT;
        total_voided := total_voided + voided_updated;

        IF paid_updated > 0 OR voided_updated > 0 THEN
            RAISE NOTICE 'migration 20260612_050000: %.invoices — paid_at 補完 % 件, voided_at 補完 % 件',
                schema_rec.nspname, paid_updated, voided_updated;
        END IF;
    END LOOP;

    RAISE NOTICE 'migration 20260612_050000: 完了。paid_at 合計 % 件, voided_at 合計 % 件', total_paid, total_voided;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
-- 補完された値は updated_at 由来であるため、NULL に戻すことで擬似ロールバック可。
-- ただし補完後の値を参照したデータが存在する場合は注意。
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         EXECUTE format($q$
--             UPDATE %I.invoices SET paid_at = NULL
--             WHERE status = 'paid' AND paid_at = COALESCE(updated_at, created_at)
--         $q$, r.nspname);
--     END LOOP;
-- END $$;
-- =====================================================================
