-- SA-02 Stage 3 / Migration 20260611_130000: v_company_stats に論理削除除外フィルタを追加
--
-- 背景:
--   SA-02 Stage 3 で conversation_logs に deleted_at カラムを追加（migration 20260611_120000）。
--   v_company_stats ビューの conversation_count / last_conversation_at 集計から
--   論理削除済みログを除外する（deleted_at IS NULL フィルタを追加）。
--
-- 依存:
--   migration 20260611_120000_add_conv_log_manual_columns.sql（deleted_at カラム追加）が先に実行済みであること
--
-- 冪等性:
--   - CREATE OR REPLACE VIEW で再実行 no-op
--
-- 適用日: 2026-06-11

DO $$
DECLARE
    schema_rec RECORD;
    applied_count INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- companies テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'companies'
        ) THEN
            CONTINUE;
        END IF;

        -- deleted_at カラムが存在するスキーマのみ対象（万一 120000 未適用の環境はスキップ）
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.nspname
              AND table_name = 'conversation_logs'
              AND column_name = 'deleted_at'
        ) THEN
            RAISE NOTICE 'migration 20260611_130000: %.conversation_logs に deleted_at なし、スキップ', schema_rec.nspname;
            CONTINUE;
        END IF;

        -- v_company_stats ビューを論理削除除外版に更新（CREATE OR REPLACE で冪等）
        EXECUTE format($q$
            CREATE OR REPLACE VIEW %I.v_company_stats AS
            SELECT
                c.id AS company_id,
                COALESCE(SUM(i.total_amount), 0) AS total_deal_amount,
                COUNT(DISTINCT d.id) AS deal_count,
                COUNT(DISTINCT cl.id) AS conversation_count,
                MAX(cl.occurred_at) AS last_conversation_at
            FROM %I.companies c
            LEFT JOIN %I.invoices i
                ON i.company_id = c.id AND i.status != 'cancelled'
            LEFT JOIN %I.deals d
                ON d.company_id = c.id
            LEFT JOIN %I.conversation_logs cl
                ON cl.company_id = c.id AND cl.deleted_at IS NULL
            GROUP BY c.id
        $q$,
            schema_rec.nspname,
            schema_rec.nspname,
            schema_rec.nspname,
            schema_rec.nspname,
            schema_rec.nspname
        );

        applied_count := applied_count + 1;
        RAISE NOTICE 'migration 20260611_130000: %.v_company_stats を論理削除除外版に更新', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260611_130000: 完了。適用 % スキーマ', applied_count;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
-- migration 20260604_100000_create_company_stats_view.sql を再実行して
-- deleted_at フィルタなし版に戻す
-- =====================================================================
