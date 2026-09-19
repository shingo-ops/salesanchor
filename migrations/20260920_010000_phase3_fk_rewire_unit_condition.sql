-- ADR-155: shared master SSOT — unit_id/condition_id UUID→INTEGER rewire (Phase 3)
-- 対象: 全 tenant_* スキーマの analysis_results
--   unit_id     UUID NULLABLE → INTEGER NULLABLE, FK 先: public.units(id)
--   condition_id UUID NOT NULL → INTEGER NOT NULL, FK 先: public.conditions(id)
-- 変換キー: public.units.code / public.conditions.code (Phase B の product_id と同パターン)

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '120s';

DO $phase3$
DECLARE
    _schema    TEXT;
    _atttypid  OID;
    _int_oid   OID := 'integer'::regtype::oid;
    _uuid_oid  OID := 'uuid'::regtype::oid;
    _bad_count INTEGER;
    _fk_name   TEXT;
BEGIN
    -- ループ: analysis_results を持つ全 tenant_* スキーマ
    FOR _schema IN
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind = 'r'
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'analysis_results'
        ORDER BY n.nspname
    LOOP
        RAISE NOTICE 'Processing schema: %', _schema;

        -- ================================================================
        -- Column 1: analysis_results.unit_id  (NULLABLE)
        -- ADR-155: unit_id UUID→INTEGER rewire (Phase 3)
        -- ================================================================
        SELECT a.atttypid INTO _atttypid
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = _schema
          AND c.relname = 'analysis_results'
          AND a.attname = 'unit_id'
          AND a.attnum > 0;

        IF _atttypid IS NULL THEN
            RAISE NOTICE '  analysis_results.unit_id does not exist in schema %, skip', _schema;
        ELSIF _atttypid = _int_oid THEN
            RAISE NOTICE '  analysis_results.unit_id already INTEGER, skip';
        ELSE
            RAISE NOTICE '  Converting analysis_results.unit_id UUID->INTEGER (NULLABLE)';

            -- Step 1: ADD tmp column
            EXECUTE format(
                'ALTER TABLE %I.analysis_results ADD COLUMN IF NOT EXISTS unit_int_id INTEGER',
                _schema
            );

            -- Step 2: UPDATE tmp via tenant units → public.units join on code
            EXECUTE format('
                UPDATE %I.analysis_results ar
                SET unit_int_id = pu.id
                FROM %I.units tu
                JOIN public.units pu ON pu.code = tu.code
                WHERE ar.unit_id = tu.id
            ', _schema, _schema);

            -- Step 3: Verify no orphaned rows (unit_id IS NOT NULL but unit_int_id IS NULL → error)
            EXECUTE format('
                SELECT COUNT(*) FROM %I.analysis_results
                WHERE unit_id IS NOT NULL AND unit_int_id IS NULL
            ', _schema) INTO _bad_count;
            IF _bad_count > 0 THEN
                RAISE EXCEPTION 'Phase 3: % rows in %.analysis_results have unit_id NOT NULL but unit_int_id IS NULL',
                    _bad_count, _schema;
            END IF;

            -- Step 4: Drop old FK pointing to tenant units (UUID)
            SELECT conname INTO _fk_name
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_class fc ON fc.oid = con.confrelid
            JOIN pg_namespace fn ON fn.oid = fc.relnamespace
            WHERE n.nspname = _schema AND c.relname = 'analysis_results'
              AND con.contype = 'f'
              AND fn.nspname = _schema AND fc.relname = 'units'
            LIMIT 1;
            IF _fk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I.analysis_results DROP CONSTRAINT %I', _schema, _fk_name);
            END IF;

            -- Step 5: Drop old UUID column
            -- ADR-155: unit_id UUID→INTEGER rewire (Phase 3)
            EXECUTE format('ALTER TABLE %I.analysis_results DROP COLUMN unit_id', _schema);

            -- Step 6: Rename tmp -> unit_id
            EXECUTE format('ALTER TABLE %I.analysis_results RENAME COLUMN unit_int_id TO unit_id', _schema);

            -- unit_id stays NULLABLE (6,668 / 10,542 件が非NULL)

            -- Step 7: Add new FK referencing public.units(id)
            EXECUTE format('
                ALTER TABLE %I.analysis_results
                ADD CONSTRAINT fk_analysis_results_unit_id
                FOREIGN KEY (unit_id) REFERENCES public.units(id)
            ', _schema);

            -- Index on unit_id
            EXECUTE format('
                CREATE INDEX IF NOT EXISTS idx_%s_ar_unit_id ON %I.analysis_results (unit_id)
            ', _schema, _schema);

            RAISE NOTICE '  analysis_results.unit_id done';
        END IF;

        -- ================================================================
        -- Column 2: analysis_results.condition_id  (全件非NULL: 10,542件)
        -- ADR-155: condition_id UUID→INTEGER rewire (Phase 3)
        -- ================================================================
        SELECT a.atttypid INTO _atttypid
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = _schema
          AND c.relname = 'analysis_results'
          AND a.attname = 'condition_id'
          AND a.attnum > 0;

        IF _atttypid IS NULL THEN
            RAISE NOTICE '  analysis_results.condition_id does not exist in schema %, skip', _schema;
        ELSIF _atttypid = _int_oid THEN
            RAISE NOTICE '  analysis_results.condition_id already INTEGER, skip';
        ELSE
            RAISE NOTICE '  Converting analysis_results.condition_id UUID->INTEGER (全件非NULL)';

            -- Step 1: ADD tmp column
            EXECUTE format(
                'ALTER TABLE %I.analysis_results ADD COLUMN IF NOT EXISTS condition_int_id INTEGER',
                _schema
            );

            -- Step 2: UPDATE tmp via tenant conditions → public.conditions join on code
            EXECUTE format('
                UPDATE %I.analysis_results ar
                SET condition_int_id = pc.id
                FROM %I.conditions tc
                JOIN public.conditions pc ON pc.code = tc.code
                WHERE ar.condition_id = tc.id
            ', _schema, _schema);

            -- Step 3: Verify no orphaned rows (全件非NULL のため必ず 0 でなければエラー)
            EXECUTE format('
                SELECT COUNT(*) FROM %I.analysis_results
                WHERE condition_id IS NOT NULL AND condition_int_id IS NULL
            ', _schema) INTO _bad_count;
            IF _bad_count > 0 THEN
                RAISE EXCEPTION 'Phase 3: % rows in %.analysis_results have condition_id NOT NULL but condition_int_id IS NULL',
                    _bad_count, _schema;
            END IF;

            -- Step 4: Drop old FK pointing to tenant conditions (UUID)
            SELECT conname INTO _fk_name
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_class fc ON fc.oid = con.confrelid
            JOIN pg_namespace fn ON fn.oid = fc.relnamespace
            WHERE n.nspname = _schema AND c.relname = 'analysis_results'
              AND con.contype = 'f'
              AND fn.nspname = _schema AND fc.relname = 'conditions'
            LIMIT 1;
            IF _fk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I.analysis_results DROP CONSTRAINT %I', _schema, _fk_name);
            END IF;

            -- Step 5: Drop old UUID column
            -- ADR-155: condition_id UUID→INTEGER rewire (Phase 3)
            EXECUTE format('ALTER TABLE %I.analysis_results DROP COLUMN condition_id', _schema);

            -- Step 6: Rename tmp -> condition_id
            EXECUTE format('ALTER TABLE %I.analysis_results RENAME COLUMN condition_int_id TO condition_id', _schema);

            -- Step 7: NOT NULL 制約を復元（元が全件非NULL）
            EXECUTE format('ALTER TABLE %I.analysis_results ALTER COLUMN condition_id SET NOT NULL', _schema);

            -- Step 8: Add new FK referencing public.conditions(id)
            EXECUTE format('
                ALTER TABLE %I.analysis_results
                ADD CONSTRAINT fk_analysis_results_condition_id
                FOREIGN KEY (condition_id) REFERENCES public.conditions(id)
            ', _schema);

            -- Index on condition_id
            EXECUTE format('
                CREATE INDEX IF NOT EXISTS idx_%s_ar_condition_id ON %I.analysis_results (condition_id)
            ', _schema, _schema);

            RAISE NOTICE '  analysis_results.condition_id done';
        END IF;

        RAISE NOTICE 'Schema % complete', _schema;
    END LOOP;
END;
$phase3$;

COMMIT;
