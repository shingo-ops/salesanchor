-- deals廃止 段階②R-2: tenant_006 の残存 8 行を削除し、deal_close_reasons / quotes の lead_id を NOT NULL 化する。
-- 方針:
--   - tenant_% スキーマを information_schema から動的列挙
--   - deal_close_reasons / quotes が存在し、lead_id 列がある場合のみ処理
--   - deal_close_reasons.lead_id IS NULL 行を削除し、その後 lead_id を NOT NULL にする
--   - quotes は現状 0 行だが、同じく NOT NULL 化して整合させる
--   - 冪等: 再実行時は削除対象 0 行・NOT NULL 既設定でも成功する

DO $$
DECLARE
    schema_rec RECORD;
    deleted_close_reasons INTEGER;
    deleted_quotes INTEGER;
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
               AND table_name = 'deal_close_reasons'
        ) THEN
            IF EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = schema_rec.schema_name
                   AND table_name = 'deal_close_reasons'
                   AND column_name = 'lead_id'
            ) THEN
                EXECUTE format(
                    'DELETE FROM %I.deal_close_reasons WHERE lead_id IS NULL',
                    schema_rec.schema_name
                );
                GET DIAGNOSTICS deleted_close_reasons = ROW_COUNT;

                EXECUTE format(
                    'ALTER TABLE %I.deal_close_reasons ALTER COLUMN lead_id SET NOT NULL',
                    schema_rec.schema_name
                );

                RAISE NOTICE 'tenant %.deal_close_reasons: deleted_null_lead_rows=%',
                    schema_rec.schema_name, deleted_close_reasons;
            END IF;
        END IF;

        IF EXISTS (
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = schema_rec.schema_name
               AND table_name = 'quotes'
        ) THEN
            IF EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = schema_rec.schema_name
                   AND table_name = 'quotes'
                   AND column_name = 'lead_id'
            ) THEN
                EXECUTE format(
                    'DELETE FROM %I.quotes WHERE lead_id IS NULL',
                    schema_rec.schema_name
                );
                GET DIAGNOSTICS deleted_quotes = ROW_COUNT;

                EXECUTE format(
                    'ALTER TABLE %I.quotes ALTER COLUMN lead_id SET NOT NULL',
                    schema_rec.schema_name
                );

                RAISE NOTICE 'tenant %.quotes: deleted_null_lead_rows=%',
                    schema_rec.schema_name, deleted_quotes;
            END IF;
        END IF;
    END LOOP;
END $$;
