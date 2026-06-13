-- =====================================================================
-- Migration: 013 - Meta Webhook冪等性とリード重複防止
-- =====================================================================
-- 目的:
--   1. meta_messagesのMeta再送による重複挿入を防止（C2）
--   2. leadsの並列リクエストによる重複作成を防止（C1）
-- 冪等性:
--   ADD COLUMN IF NOT EXISTS / CREATE UNIQUE INDEX IF NOT EXISTS を使用
--   何度実行しても安全
-- 既存データへの影響:
--   - message_id列はNULL許可で追加するため既存行に影響なし
--   - leads UNIQUE INDEX追加前に重複を検出した場合はWARNINGを出してスキップ
-- =====================================================================

DO $$
DECLARE
    schema_record  RECORD;
    duplicate_count INTEGER;
BEGIN
    FOR schema_record IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Processing schema: %', schema_record.schema_name;

        -- ============================================================
        -- C2: meta_messages に message_id 列を追加
        --     NULL許可（既存行・mid未取得メッセージへの影響なし）
        --     meta_messages テーブルが存在する場合のみ実行（migrate_meta.py依存）。
        -- ADR-036 整合: 部分テナントや migration 単体検証で meta_messages が無い
        --     場合でも abort せず WARNING で loud-skip する（C1 と同方針）。
        -- ============================================================
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_record.schema_name
              AND table_name = 'meta_messages'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.meta_messages
                 ADD COLUMN IF NOT EXISTS message_id VARCHAR(100)',
                schema_record.schema_name
            );

            -- message_id の UNIQUE 部分インデックス（NULL は除外）
            EXECUTE format(
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_meta_messages_message_id_unique
                 ON %I.meta_messages (message_id)
                 WHERE message_id IS NOT NULL',
                schema_record.schema_name
            );

            RAISE NOTICE 'meta_messages: message_id column and unique index applied for %',
                schema_record.schema_name;
        ELSE
            RAISE WARNING
                'Schema %: meta_messages テーブルが存在しないため message_id 列追加を '
                'スキップしました（ADR-036: loud-skip）。',
                schema_record.schema_name;
        END IF;

        -- ============================================================
        -- C1: leads(source) に UNIQUE 部分インデックスを追加
        --     source 列が存在する場合のみ実行。
        --     ADR-138 §D1-3（クリーンスレート）により migration 20260613_030000 が
        --     leads.source を廃止済みのため、列が無い場合はスキップする（loud-skip）。
        -- ADR-036 整合: 欠落時は WARNING を出して loud-skip（silent ではない）。
        -- ============================================================
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_record.schema_name
              AND table_name = 'leads'
              AND column_name = 'source'
        ) THEN
            EXECUTE format(
                'SELECT COUNT(*) FROM (
                    SELECT source
                    FROM %I.leads
                    WHERE source LIKE ''messenger:%%''
                       OR source LIKE ''instagram:%%''
                    GROUP BY source
                    HAVING COUNT(*) > 1
                ) dup',
                schema_record.schema_name
            ) INTO duplicate_count;

            IF duplicate_count > 0 THEN
                RAISE WARNING
                    'Schema % has % duplicate leads with meta source. '
                    'UNIQUE index idx_leads_meta_source_unique creation SKIPPED. '
                    'Manually deduplicate before re-running.',
                    schema_record.schema_name, duplicate_count;
            ELSE
                EXECUTE format(
                    'CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_meta_source_unique
                     ON %I.leads (source)
                     WHERE source LIKE ''messenger:%%''
                        OR source LIKE ''instagram:%%''',
                    schema_record.schema_name
                );
                RAISE NOTICE 'leads: UNIQUE index idx_leads_meta_source_unique created for %',
                    schema_record.schema_name;
            END IF;
        ELSE
            RAISE WARNING
                'Schema %: leads.source 列が存在しないため meta-source UNIQUE index を '
                'スキップしました（migration 103 適用済み・ADR-138 §D1-3）。',
                schema_record.schema_name;
        END IF;

    END LOOP;

    RAISE NOTICE 'Migration 013 completed.';
END $$;

-- =====================================================================
-- Rollback手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE
--     r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%'
--     LOOP
--         EXECUTE format('DROP INDEX IF EXISTS %I.idx_meta_messages_message_id_unique', r.nspname);
--         EXECUTE format('DROP INDEX IF EXISTS %I.idx_leads_meta_source_unique', r.nspname);
--         EXECUTE format('ALTER TABLE %I.meta_messages DROP COLUMN IF EXISTS message_id', r.nspname);
--     END LOOP;
-- END $$;
-- =====================================================================
