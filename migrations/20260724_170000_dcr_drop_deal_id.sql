-- deal-removal: deal_close_reasons から deal_id 依存を撤去し、lead_id 経路を一意化する。
-- 対象は pg_namespace 上の tenant_% スキーマのみ。全操作は存在確認付きで冪等。

DO $$
DECLARE
    schema_rec RECORD;
    has_table BOOLEAN;
    has_fk BOOLEAN;
    has_deal_unique BOOLEAN;
    has_deal_index BOOLEAN;
    has_deal_id BOOLEAN;
    has_lead_unique BOOLEAN;
    fk_applied INTEGER := 0;
    deal_unique_applied INTEGER := 0;
    deal_index_applied INTEGER := 0;
    deal_id_applied INTEGER := 0;
    lead_unique_applied INTEGER := 0;
    tenant_count INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname
        FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        SELECT EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = schema_rec.nspname
              AND c.relname = 'deal_close_reasons'
              AND c.relkind IN ('r', 'p')
        ) INTO has_table;

        IF NOT has_table THEN
            RAISE NOTICE 'dcr_drop_deal_id: %: deal_close_reasons がないため skip', schema_rec.nspname;
            CONTINUE;
        END IF;

        tenant_count := tenant_count + 1;

        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = schema_rec.nspname
              AND c.relname = 'deal_close_reasons'
              AND con.conname = 'deal_close_reasons_deal_id_fkey'
        ) INTO has_fk;
        IF has_fk THEN
            EXECUTE format(
                'ALTER TABLE %I.deal_close_reasons DROP CONSTRAINT deal_close_reasons_deal_id_fkey',
                schema_rec.nspname
            );
            fk_applied := fk_applied + 1;
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = schema_rec.nspname
              AND c.relname = 'deal_close_reasons'
              AND con.conname = 'deal_close_reasons_deal_id_reason_id_key'
        ) INTO has_deal_unique;
        IF has_deal_unique THEN
            EXECUTE format(
                'ALTER TABLE %I.deal_close_reasons DROP CONSTRAINT deal_close_reasons_deal_id_reason_id_key',
                schema_rec.nspname
            );
            deal_unique_applied := deal_unique_applied + 1;
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = schema_rec.nspname
              AND c.relname = 'idx_deal_close_reasons_deal'
              AND c.relkind = 'i'
        ) INTO has_deal_index;
        IF has_deal_index THEN
            EXECUTE format('DROP INDEX %I.idx_deal_close_reasons_deal', schema_rec.nspname);
            deal_index_applied := deal_index_applied + 1;
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = schema_rec.nspname
              AND c.relname = 'deal_close_reasons'
              AND a.attname = 'deal_id'
              AND NOT a.attisdropped
        ) INTO has_deal_id;
        IF has_deal_id THEN
            EXECUTE format('ALTER TABLE %I.deal_close_reasons DROP COLUMN deal_id', schema_rec.nspname);
            deal_id_applied := deal_id_applied + 1;
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = schema_rec.nspname
              AND c.relname = 'deal_close_reasons'
              AND con.contype = 'u'
              AND con.conkey = ARRAY[
                  (SELECT a.attnum FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attname = 'lead_id' AND NOT a.attisdropped),
                  (SELECT a.attnum FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attname = 'reason_id' AND NOT a.attisdropped)
              ]::smallint[]
        ) INTO has_lead_unique;
        IF NOT has_lead_unique THEN
            EXECUTE format(
                'ALTER TABLE %I.deal_close_reasons ADD CONSTRAINT deal_close_reasons_lead_id_reason_id_key UNIQUE (lead_id, reason_id)',
                schema_rec.nspname
            );
            lead_unique_applied := lead_unique_applied + 1;
        END IF;

        RAISE NOTICE 'dcr_drop_deal_id: %: fk=%, deal_unique=%, deal_index=%, deal_id=%, lead_unique=%',
            schema_rec.nspname,
            CASE WHEN has_fk THEN 'applied' ELSE 'skipped' END,
            CASE WHEN has_deal_unique THEN 'applied' ELSE 'skipped' END,
            CASE WHEN has_deal_index THEN 'applied' ELSE 'skipped' END,
            CASE WHEN has_deal_id THEN 'applied' ELSE 'skipped' END,
            CASE WHEN has_lead_unique THEN 'skipped' ELSE 'applied' END;
    END LOOP;

    RAISE NOTICE 'dcr_drop_deal_id summary: tenants=%, fk_applied=%, deal_unique_applied=%, deal_index_applied=%, deal_id_applied=%, lead_unique_applied=%',
        tenant_count, fk_applied, deal_unique_applied, deal_index_applied, deal_id_applied, lead_unique_applied;
END $$;
