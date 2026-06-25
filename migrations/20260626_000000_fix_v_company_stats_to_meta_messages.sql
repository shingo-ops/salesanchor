-- ============================================================================
-- Migration: 20260626_000000
-- v_company_stats の集計元を conversation_logs → meta_messages に変更
--
-- 背景（SA-02 G1b 追補）:
--   #2600 で手動記録の書き込み先を meta_messages (is_manual=true) に変更した。
--   v_company_stats が conversation_logs を読み続けると新規手動記録を取りこぼすため、
--   集計元を ① meta_messages に統一する。
--
-- 変更ルール:
--   - 数え方・除外条件の意味は変えない（conversation_count の定義を変えない）
--   - conversation_logs の削除フィルタが元々なかったため meta_messages でも同様
--   - ② conversation_logs・データは消さない（ロールバック余地を残す）
--   - 既存の invoices / deals の集計ロジックは一切変えない
--
-- 冪等: DROP + CREATE で再実行可能
-- 対象: tenant_[0-9]+ スキーマ全件
-- ============================================================================

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
        -- companies と meta_messages の両方が存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'companies'
        ) THEN
            CONTINUE;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'meta_messages'
        ) THEN
            CONTINUE;
        END IF;

        -- v_company_stats ビュー再作成（DROP → CREATE で冪等）
        -- CREATE OR REPLACE はカラム名変更不可のため DROP を先行する（ADR-136）
        EXECUTE format('DROP VIEW IF EXISTS %I.v_company_stats CASCADE', schema_rec.nspname);

        EXECUTE format($q$
            CREATE VIEW %I.v_company_stats AS
            -- サブクエリで先に集計してから c に JOIN することで
            -- 横並び JOIN による SUM ファンアウトを防ぐ（ADR-136 §Fan-out 対策）
            SELECT
                c.id                                    AS company_id,
                COALESCE(inv.total_deal_amount, 0)      AS total_deal_amount,
                COALESCE(inv.paid_invoice_count, 0)     AS paid_invoice_count,
                inv.last_paid_at                        AS last_paid_at,
                COALESCE(d.deal_count, 0)               AS deal_count,
                COALESCE(mm.conversation_count, 0)      AS conversation_count,
                mm.last_conversation_at                 AS last_conversation_at
            FROM %I.companies c
            LEFT JOIN (
                SELECT company_id,
                       SUM(total_amount)  AS total_deal_amount,
                       COUNT(*)           AS paid_invoice_count,
                       MAX(paid_at)       AS last_paid_at
                FROM %I.invoices
                WHERE paid_at IS NOT NULL AND voided_at IS NULL
                GROUP BY company_id
            ) inv ON inv.company_id = c.id
            LEFT JOIN (
                SELECT company_id,
                       COUNT(*)           AS deal_count
                FROM %I.deals
                GROUP BY company_id
            ) d ON d.company_id = c.id
            LEFT JOIN (
                SELECT company_id,
                       COUNT(*)           AS conversation_count,
                       MAX(occurred_at)   AS last_conversation_at
                FROM %I.meta_messages
                GROUP BY company_id
            ) mm ON mm.company_id = c.id
        $q$,
            schema_rec.nspname,  -- outer SELECT
            schema_rec.nspname,  -- companies
            schema_rec.nspname,  -- invoices subquery
            schema_rec.nspname,  -- deals subquery
            schema_rec.nspname   -- meta_messages subquery
        );

        applied_count := applied_count + 1;
        RAISE NOTICE 'migration 20260626_000000: %.v_company_stats を meta_messages ベースで再作成', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260626_000000: 完了。適用 % スキーマ', applied_count;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行・20260612_120000_fix_company_stats_ssot.sql を再適用）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         EXECUTE format('DROP VIEW IF EXISTS %I.v_company_stats CASCADE', r.nspname);
--         EXECUTE format($q$
--             CREATE VIEW %I.v_company_stats AS
--             SELECT
--                 c.id AS company_id,
--                 COALESCE(SUM(i.total_amount), 0) AS total_deal_amount,
--                 COUNT(DISTINCT i.id)              AS paid_invoice_count,
--                 MAX(i.paid_at)                    AS last_paid_at,
--                 COUNT(DISTINCT d.id)              AS deal_count,
--                 COUNT(DISTINCT cl.id)             AS conversation_count,
--                 MAX(cl.occurred_at)               AS last_conversation_at
--             FROM %I.companies c
--             LEFT JOIN %I.invoices i
--                 ON i.company_id = c.id AND i.paid_at IS NOT NULL AND i.voided_at IS NULL
--             LEFT JOIN %I.deals d ON d.company_id = c.id
--             LEFT JOIN %I.conversation_logs cl ON cl.company_id = c.id
--             GROUP BY c.id
--         $q$, r.nspname, r.nspname, r.nspname, r.nspname, r.nspname);
--     END LOOP;
-- END $$;
-- =====================================================================
