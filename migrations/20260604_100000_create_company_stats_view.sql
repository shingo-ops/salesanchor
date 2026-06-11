-- SA-02 / Migration 20260604_100000: v_company_stats ビュー作成
--
-- 背景:
--   会社詳細ページに集計情報（累計取引額・商談数・会話数・最終会話日時）を
--   表示するための読み取り専用集計ビュー。
--
-- 設計:
--   - invoices（請求書）から累計金額を集計（quotes=見積 ではない）。
--   - status != 'cancelled' フィルタ: 再発行フロー（キャンセル+新規）を考慮し
--     キャンセル済み請求書を除外する。
--   - CREATE OR REPLACE VIEW で冪等。
--   - conversation_logs は migration 20260604_070000 で作成済みの前提。
--
-- 冪等性:
--   - CREATE OR REPLACE VIEW で再実行 no-op（ビュー定義が変わっても安全）
--
-- 作成日: 2026-06-04

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

        -- v_company_stats ビュー作成（CREATE OR REPLACE で冪等）
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
        RAISE NOTICE 'migration 20260604_100000: %.v_company_stats を作成', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260604_100000: 完了。適用 % スキーマ', applied_count;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         EXECUTE format('DROP VIEW IF EXISTS %I.v_company_stats', r.nspname);
--     END LOOP;
-- END $$;
-- =====================================================================
