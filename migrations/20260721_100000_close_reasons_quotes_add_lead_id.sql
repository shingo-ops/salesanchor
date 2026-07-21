-- deals廃止 段階②R: deal_close_reasons / quotes に lead_id を追加する。
-- 方針:
--   - deal_close_reasons.lead_id / quotes.lead_id は nullable で追加し、leads FK を付与する
--   - 既存の壊れた行（tenant_006 の close reason 8 行など）は null のまま残す
--   - NOT NULL 化は tenant_006 の 8 行整理後に別 migration で実施する
-- 冪等:
--   - information_schema で tenant_% スキーマを動的列挙
--   - 対象テーブル・対象列がある場合のみ処理
--   - 再実行で no-op

DO $$
DECLARE
    schema_rec RECORD;
    applied_quotes INTEGER := 0;
    applied_close_reasons INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT schema_name
          FROM information_schema.schemata
         WHERE schema_name LIKE 'tenant_%'
         ORDER BY schema_name
    LOOP
        IF EXISTS (
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = schema_rec.schema_name
               AND table_name = 'quotes'
        ) THEN
            IF NOT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = schema_rec.schema_name
                   AND table_name = 'quotes'
                   AND column_name = 'lead_id'
            ) THEN
                EXECUTE format(
                    'ALTER TABLE %I.quotes ADD COLUMN lead_id INTEGER',
                    schema_rec.schema_name
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'fk_quotes_lead'
                   AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = schema_rec.schema_name)
            ) THEN
                EXECUTE format(
                    'ALTER TABLE %I.quotes ADD CONSTRAINT fk_quotes_lead FOREIGN KEY (lead_id) REFERENCES %I.leads(id)',
                    schema_rec.schema_name, schema_rec.schema_name
                );
            END IF;

            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_quotes_lead_id ON %I.quotes (lead_id)', schema_rec.schema_name);
            applied_quotes := applied_quotes + 1;
        END IF;

        IF EXISTS (
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = schema_rec.schema_name
               AND table_name = 'deal_close_reasons'
        ) THEN
            IF NOT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = schema_rec.schema_name
                   AND table_name = 'deal_close_reasons'
                   AND column_name = 'lead_id'
            ) THEN
                EXECUTE format(
                    'ALTER TABLE %I.deal_close_reasons ADD COLUMN lead_id INTEGER',
                    schema_rec.schema_name
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'fk_deal_close_reasons_lead'
                   AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = schema_rec.schema_name)
            ) THEN
                EXECUTE format(
                    'ALTER TABLE %I.deal_close_reasons ADD CONSTRAINT fk_deal_close_reasons_lead FOREIGN KEY (lead_id) REFERENCES %I.leads(id)',
                    schema_rec.schema_name, schema_rec.schema_name
                );
            END IF;

            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_deal_close_reasons_lead_id ON %I.deal_close_reasons (lead_id)', schema_rec.schema_name);
            applied_close_reasons := applied_close_reasons + 1;
        END IF;
    END LOOP;

    RAISE NOTICE 'deal_close_reasons/quotes lead_id migration done. quotes=% close_reasons=%',
        applied_quotes, applied_close_reasons;
END $$;
