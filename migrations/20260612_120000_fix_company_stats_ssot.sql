-- ADR-137: v_company_stats SSOT 修正
-- 取引額集計のフィルタを `status != 'cancelled'` から
-- `paid_at IS NOT NULL AND voided_at IS NULL` へ変更し、
-- ADR-108 の公式定義に統一する。
-- paid_invoice_count / last_paid_at カラムを追加し、
-- カルテ表示に必要な全値をビュー一本で賄えるようにする。

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

        -- v_company_stats ビュー再作成（DROP → CREATE で冪等）
        -- CREATE OR REPLACE はカラム名変更不可のため DROP を先行する（ADR-136）
        -- フィルタを paid_at IS NOT NULL AND voided_at IS NULL に変更
        EXECUTE format('DROP VIEW IF EXISTS %I.v_company_stats CASCADE', schema_rec.nspname);

        EXECUTE format($q$
            CREATE VIEW %I.v_company_stats AS
            SELECT
                c.id AS company_id,
                COALESCE(SUM(i.total_amount), 0)                       AS total_deal_amount,
                COUNT(DISTINCT i.id)                                    AS paid_invoice_count,
                MAX(i.paid_at)                                          AS last_paid_at,
                COUNT(DISTINCT d.id)                                    AS deal_count,
                COUNT(DISTINCT cl.id)                                   AS conversation_count,
                MAX(cl.occurred_at)                                     AS last_conversation_at
            FROM %I.companies c
            LEFT JOIN %I.invoices i
                ON i.company_id = c.id
                AND i.paid_at IS NOT NULL
                AND i.voided_at IS NULL
            LEFT JOIN %I.deals d
                ON d.company_id = c.id
            LEFT JOIN %I.conversation_logs cl
                ON cl.company_id = c.id
            GROUP BY c.id
        $q$,
            schema_rec.nspname,
            schema_rec.nspname,
            schema_rec.nspname,
            schema_rec.nspname,
            schema_rec.nspname
        );

        applied_count := applied_count + 1;
        RAISE NOTICE 'migration 20260612_100000: %.v_company_stats を再作成', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260612_100000: 完了。適用 % スキーマ', applied_count;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行・前の migration を再適用）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         EXECUTE format($q$
--             CREATE OR REPLACE VIEW %I.v_company_stats AS
--             SELECT
--                 c.id AS company_id,
--                 COALESCE(SUM(i.total_amount), 0) AS total_deal_amount,
--                 COUNT(DISTINCT d.id) AS deal_count,
--                 COUNT(DISTINCT cl.id) AS conversation_count,
--                 MAX(cl.occurred_at) AS last_conversation_at
--             FROM %I.companies c
--             LEFT JOIN %I.invoices i
--                 ON i.company_id = c.id AND i.status != ''cancelled''
--             LEFT JOIN %I.deals d ON d.company_id = c.id
--             LEFT JOIN %I.conversation_logs cl ON cl.company_id = c.id
--             GROUP BY c.id
--         $q$, r.nspname, r.nspname, r.nspname, r.nspname, r.nspname);
--     END LOOP;
-- END $$;
-- =====================================================================
