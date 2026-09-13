-- deals廃止 段階2-R-2: deal_close_reasons.deal_id の NOT NULL を解除する。
-- 方針:
--   - tenant_% スキーマを information_schema から動的列挙
--   - deal_close_reasons と deal_id 列が実在するもののみ適用
--   - 既に nullable ならスキップ
--   - 冪等: 何度流しても同じ状態に収束する

DO $$
DECLARE
    schema_rec RECORD;
    applied_count INTEGER := 0;
    skipped_no_table INTEGER := 0;
    skipped_no_column INTEGER := 0;
    skipped_already_nullable INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT schema_name
          FROM information_schema.schemata
         WHERE schema_name LIKE 'tenant_%'
         ORDER BY schema_name
    LOOP
        IF NOT EXISTS (
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = schema_rec.schema_name
               AND table_name = 'deal_close_reasons'
        ) THEN
            skipped_no_table := skipped_no_table + 1;
            CONTINUE;
        END IF;

        IF NOT EXISTS (
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = schema_rec.schema_name
               AND table_name = 'deal_close_reasons'
               AND column_name = 'deal_id'
        ) THEN
            skipped_no_column := skipped_no_column + 1;
            CONTINUE;
        END IF;

        IF EXISTS (
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = schema_rec.schema_name
               AND table_name = 'deal_close_reasons'
               AND column_name = 'deal_id'
               AND is_nullable = 'NO'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.deal_close_reasons ALTER COLUMN deal_id DROP NOT NULL',
                schema_rec.schema_name
            );
            applied_count := applied_count + 1;
            RAISE NOTICE 'tenant %.deal_close_reasons: deal_id set nullable', schema_rec.schema_name;
        ELSE
            skipped_already_nullable := skipped_already_nullable + 1;
            RAISE NOTICE 'tenant %.deal_close_reasons: deal_id already nullable, skipped', schema_rec.schema_name;
        END IF;
    END LOOP;

    RAISE NOTICE
        'deal_close_reasons.deal_id not-null drop done. applied=% skipped_no_table=% skipped_no_column=% skipped_already_nullable=%',
        applied_count, skipped_no_table, skipped_no_column, skipped_already_nullable;
END $$;
