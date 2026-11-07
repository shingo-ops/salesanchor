-- 会話の一本化 便1: v_company_stats の会話の数え方を meta_messages に付け替える
--
-- 今までは会社の「会話の数」と「最後の会話の日時」を、二重に書いていた会話の表から数えていた。
-- 便1 で会話の書き込みと読み込みを meta_messages だけにするため、集計ビューも同じ表から数える。
--
-- 方針:
--   * 列の名前・順番・型は今のビューと同じ（company_id・total_deal_amount・paid_invoice_count・
--     last_paid_at・deal_count・conversation_count・last_conversation_at の順）
--   * CREATE OR REPLACE VIEW で作り直す（消さない。列が同じなので置き換えられる）
--   * 値を変える文（挿入・更新・削除）は書かない（ADR-1007）
--   * 次の3つが全部あるスキーマだけ対象: companies 表、meta_messages 表、
--     meta_messages の company_id・occurred_at・deleted_at の3列。無ければ NOTICE を出して飛ばす
--   * 冪等: 何度流しても同じ結果
--
-- 型の根拠: last_conversation_at は MAX(COALESCE(m.occurred_at, m.created_at))。
--   meta_messages.occurred_at と created_at はどちらも TIMESTAMPTZ なので、今のビューと同じ型。

DO $$
DECLARE
    schema_rec RECORD;
    applied_count INTEGER := 0;
    skipped_count INTEGER := 0;
    col_count INTEGER;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- companies 表が無ければ飛ばす
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.nspname AND table_name = 'companies'
        ) THEN
            RAISE NOTICE 'migration 20261108_100000: %.companies が無いので飛ばす', schema_rec.nspname;
            skipped_count := skipped_count + 1;
            CONTINUE;
        END IF;

        -- meta_messages 表が無ければ飛ばす
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.nspname AND table_name = 'meta_messages'
        ) THEN
            RAISE NOTICE 'migration 20261108_100000: %.meta_messages が無いので飛ばす', schema_rec.nspname;
            skipped_count := skipped_count + 1;
            CONTINUE;
        END IF;

        -- meta_messages の3列（company_id・occurred_at・deleted_at）が全部無ければ飛ばす
        SELECT COUNT(*) INTO col_count
        FROM information_schema.columns
        WHERE table_schema = schema_rec.nspname
          AND table_name = 'meta_messages'
          AND column_name IN ('company_id', 'occurred_at', 'deleted_at');
        IF col_count < 3 THEN
            RAISE NOTICE 'migration 20261108_100000: %.meta_messages に company_id・occurred_at・deleted_at の3列がそろっていないので飛ばす',
                schema_rec.nspname;
            skipped_count := skipped_count + 1;
            CONTINUE;
        END IF;

        EXECUTE format($q$
            CREATE OR REPLACE VIEW %I.v_company_stats AS
            SELECT
                c.id AS company_id,
                COALESCE(SUM(i.total_amount), 0)                                                     AS total_deal_amount,
                COUNT(DISTINCT i.id)                                                                  AS paid_invoice_count,
                MAX(i.paid_at)                                                                        AS last_paid_at,
                COUNT(CASE WHEN l.status IN ('negotiating', 'existing_customer', 'lost') THEN 1 END) AS deal_count,
                COUNT(DISTINCT m.id)                                                                  AS conversation_count,
                MAX(COALESCE(m.occurred_at, m.created_at))                                            AS last_conversation_at
            FROM %I.companies c
            LEFT JOIN %I.invoices i
                ON i.company_id = c.id
                AND i.paid_at IS NOT NULL
                AND i.voided_at IS NULL
            LEFT JOIN %I.leads l
                ON l.id = c.lead_id
            LEFT JOIN %I.meta_messages m
                ON m.company_id = c.id
                AND m.deleted_at IS NULL
            GROUP BY c.id
        $q$, schema_rec.nspname, schema_rec.nspname, schema_rec.nspname,
             schema_rec.nspname, schema_rec.nspname);

        RAISE NOTICE 'migration 20261108_100000: %.v_company_stats を meta_messages で作り直し', schema_rec.nspname;
        applied_count := applied_count + 1;
    END LOOP;

    RAISE NOTICE 'migration 20261108_100000: 作り直し % 社 / 飛ばし % 社', applied_count, skipped_count;
END $$;

-- =====================================================================
-- 戻し方:
--   migrations/20260612_120000_fix_company_stats_ssot.sql の CREATE 部分を CREATE OR REPLACE にして流す
--   （列が同じなので、ビューを消す必要はない）
-- =====================================================================
