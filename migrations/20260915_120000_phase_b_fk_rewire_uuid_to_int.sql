-- ADR-1002 Phase B: FK付替え UUID→INTEGER + SEQUENCE（冪等）
-- 対象: 全 tenant_* スキーマの 4テーブル
--   product_search_keywords, product_exclude_keywords, products_logistics, analysis_results
-- 変換: product_id UUID → INTEGER, FK 先: public.products(tcg_uuid) → public.products(id)

DO $phase_b$
DECLARE
    _schema    TEXT;
    _atttypid  OID;
    _int_oid   OID := 'integer'::regtype::oid;
    _uuid_oid  OID := 'uuid'::regtype::oid;
    _bad_count INTEGER;
    _fk_name   TEXT;
    _idx       RECORD;
BEGIN
    -- ループ: product_search_keywords を持つ全 tenant_* スキーマ
    FOR _schema IN
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind = 'r'
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'product_search_keywords'
        ORDER BY n.nspname
    LOOP
        RAISE NOTICE 'Processing schema: %', _schema;

        -- ================================================================
        -- Table 1: product_search_keywords  (product_id NOT NULL)
        -- ================================================================
        SELECT a.atttypid INTO _atttypid
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = _schema
          AND c.relname = 'product_search_keywords'
          AND a.attname = 'product_id'
          AND a.attnum > 0;

        IF _atttypid = _int_oid THEN
            RAISE NOTICE '  product_search_keywords.product_id already INTEGER, skip';
        ELSE
            RAISE NOTICE '  Converting product_search_keywords.product_id UUID->INTEGER';

            -- Step 1: ADD tmp column
            EXECUTE format('ALTER TABLE %I.product_search_keywords ADD COLUMN IF NOT EXISTS product_int_id INTEGER', _schema);

            -- Step 2: UPDATE tmp from public.products.id via tcg_uuid join
            EXECUTE format('
                UPDATE %I.product_search_keywords sk
                SET product_int_id = p.id
                FROM public.products p
                WHERE p.tcg_uuid = sk.product_id
            ', _schema);

            -- Step 3: Verify no orphaned rows
            EXECUTE format('
                SELECT COUNT(*) FROM %I.product_search_keywords
                WHERE product_id IS NOT NULL AND product_int_id IS NULL
            ', _schema) INTO _bad_count;
            IF _bad_count > 0 THEN
                RAISE EXCEPTION 'Phase B: % rows in %.product_search_keywords have product_id NOT NULL but product_int_id IS NULL',
                    _bad_count, _schema;
            END IF;

            -- Step 4: Drop old FK (tcg_uuid-pointing)
            SELECT conname INTO _fk_name
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_class fc ON fc.oid = con.confrelid
            JOIN pg_namespace fn ON fn.oid = fc.relnamespace
            WHERE n.nspname = _schema AND c.relname = 'product_search_keywords'
              AND con.contype = 'f'
              AND fn.nspname = 'public' AND fc.relname = 'products'
            LIMIT 1;
            IF _fk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I.product_search_keywords DROP CONSTRAINT %I', _schema, _fk_name);
            END IF;

            -- Step 5: Drop old UUID column
            EXECUTE format('ALTER TABLE %I.product_search_keywords DROP COLUMN product_id', _schema);

            -- Step 6: Rename tmp -> product_id
            EXECUTE format('ALTER TABLE %I.product_search_keywords RENAME COLUMN product_int_id TO product_id', _schema);

            -- Step 7: NOT NULL constraint
            EXECUTE format('ALTER TABLE %I.product_search_keywords ALTER COLUMN product_id SET NOT NULL', _schema);

            -- Step 8: Add new FK referencing public.products(id) CASCADE
            EXECUTE format('
                ALTER TABLE %I.product_search_keywords
                ADD CONSTRAINT fk_product_search_keywords_product_id
                FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE
            ', _schema);

            -- Step 9: Index on product_id
            EXECUTE format('
                CREATE INDEX IF NOT EXISTS idx_%s_psk_product_id ON %I.product_search_keywords (product_id)
            ', _schema, _schema);

            RAISE NOTICE '  product_search_keywords done';
        END IF;

        -- ================================================================
        -- Table 2: product_exclude_keywords  (product_id NOT NULL)
        -- ================================================================
        SELECT a.atttypid INTO _atttypid
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = _schema
          AND c.relname = 'product_exclude_keywords'
          AND a.attname = 'product_id'
          AND a.attnum > 0;

        IF _atttypid = _int_oid THEN
            RAISE NOTICE '  product_exclude_keywords.product_id already INTEGER, skip';
        ELSE
            RAISE NOTICE '  Converting product_exclude_keywords.product_id UUID->INTEGER';

            EXECUTE format('ALTER TABLE %I.product_exclude_keywords ADD COLUMN IF NOT EXISTS product_int_id INTEGER', _schema);

            EXECUTE format('
                UPDATE %I.product_exclude_keywords ek
                SET product_int_id = p.id
                FROM public.products p
                WHERE p.tcg_uuid = ek.product_id
            ', _schema);

            EXECUTE format('
                SELECT COUNT(*) FROM %I.product_exclude_keywords
                WHERE product_id IS NOT NULL AND product_int_id IS NULL
            ', _schema) INTO _bad_count;
            IF _bad_count > 0 THEN
                RAISE EXCEPTION 'Phase B: % rows in %.product_exclude_keywords have product_id NOT NULL but product_int_id IS NULL',
                    _bad_count, _schema;
            END IF;

            SELECT conname INTO _fk_name
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_class fc ON fc.oid = con.confrelid
            JOIN pg_namespace fn ON fn.oid = fc.relnamespace
            WHERE n.nspname = _schema AND c.relname = 'product_exclude_keywords'
              AND con.contype = 'f'
              AND fn.nspname = 'public' AND fc.relname = 'products'
            LIMIT 1;
            IF _fk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I.product_exclude_keywords DROP CONSTRAINT %I', _schema, _fk_name);
            END IF;

            EXECUTE format('ALTER TABLE %I.product_exclude_keywords DROP COLUMN product_id', _schema);
            EXECUTE format('ALTER TABLE %I.product_exclude_keywords RENAME COLUMN product_int_id TO product_id', _schema);
            EXECUTE format('ALTER TABLE %I.product_exclude_keywords ALTER COLUMN product_id SET NOT NULL', _schema);
            EXECUTE format('
                ALTER TABLE %I.product_exclude_keywords
                ADD CONSTRAINT fk_product_exclude_keywords_product_id
                FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE
            ', _schema);
            EXECUTE format('
                CREATE INDEX IF NOT EXISTS idx_%s_pek_product_id ON %I.product_exclude_keywords (product_id)
            ', _schema, _schema);

            RAISE NOTICE '  product_exclude_keywords done';
        END IF;

        -- ================================================================
        -- Table 3: products_logistics  (product_id = PRIMARY KEY)
        -- ================================================================
        -- Check if table exists first
        IF EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = _schema AND c.relname = 'products_logistics' AND c.relkind = 'r'
        ) THEN
            SELECT a.atttypid INTO _atttypid
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = _schema
              AND c.relname = 'products_logistics'
              AND a.attname = 'product_id'
              AND a.attnum > 0;

            IF _atttypid = _int_oid THEN
                RAISE NOTICE '  products_logistics.product_id already INTEGER, skip';
            ELSE
                RAISE NOTICE '  Converting products_logistics.product_id UUID->INTEGER (PK table)';

                EXECUTE format('ALTER TABLE %I.products_logistics ADD COLUMN IF NOT EXISTS product_int_id INTEGER', _schema);

                EXECUTE format('
                    UPDATE %I.products_logistics pl
                    SET product_int_id = p.id
                    FROM public.products p
                    WHERE p.tcg_uuid = pl.product_id
                ', _schema);

                EXECUTE format('
                    SELECT COUNT(*) FROM %I.products_logistics
                    WHERE product_id IS NOT NULL AND product_int_id IS NULL
                ', _schema) INTO _bad_count;
                IF _bad_count > 0 THEN
                    RAISE EXCEPTION 'Phase B: % rows in %.products_logistics have product_id NOT NULL but product_int_id IS NULL',
                        _bad_count, _schema;
                END IF;

                -- Drop PK constraint first (product_id is PK)
                SELECT conname INTO _fk_name
                FROM pg_constraint con
                JOIN pg_class c ON c.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = _schema AND c.relname = 'products_logistics'
                  AND con.contype = 'p'
                LIMIT 1;
                IF _fk_name IS NOT NULL THEN
                    EXECUTE format('ALTER TABLE %I.products_logistics DROP CONSTRAINT %I', _schema, _fk_name);
                END IF;

                -- Drop FK constraint pointing to public.products(tcg_uuid)
                SELECT conname INTO _fk_name
                FROM pg_constraint con
                JOIN pg_class c ON c.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_class fc ON fc.oid = con.confrelid
                JOIN pg_namespace fn ON fn.oid = fc.relnamespace
                WHERE n.nspname = _schema AND c.relname = 'products_logistics'
                  AND con.contype = 'f'
                  AND fn.nspname = 'public' AND fc.relname = 'products'
                LIMIT 1;
                IF _fk_name IS NOT NULL THEN
                    EXECUTE format('ALTER TABLE %I.products_logistics DROP CONSTRAINT %I', _schema, _fk_name);
                END IF;

                EXECUTE format('ALTER TABLE %I.products_logistics DROP COLUMN product_id', _schema);
                EXECUTE format('ALTER TABLE %I.products_logistics RENAME COLUMN product_int_id TO product_id', _schema);
                EXECUTE format('ALTER TABLE %I.products_logistics ALTER COLUMN product_id SET NOT NULL', _schema);
                -- Re-add PK
                EXECUTE format('ALTER TABLE %I.products_logistics ADD PRIMARY KEY (product_id)', _schema);
                -- Add FK referencing public.products(id)
                EXECUTE format('
                    ALTER TABLE %I.products_logistics
                    ADD CONSTRAINT fk_products_logistics_product_id
                    FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE
                ', _schema);

                RAISE NOTICE '  products_logistics done';
            END IF;
        ELSE
            RAISE NOTICE '  products_logistics does not exist in schema %, skip', _schema;
        END IF;

        -- ================================================================
        -- Table 4: analysis_results  (product_id NULLABLE)
        -- ================================================================
        IF EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = _schema AND c.relname = 'analysis_results' AND c.relkind = 'r'
        ) THEN
            SELECT a.atttypid INTO _atttypid
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = _schema
              AND c.relname = 'analysis_results'
              AND a.attname = 'product_id'
              AND a.attnum > 0;

            IF _atttypid = _int_oid THEN
                RAISE NOTICE '  analysis_results.product_id already INTEGER, skip';
            ELSE
                RAISE NOTICE '  Converting analysis_results.product_id UUID->INTEGER (NULLABLE)';

                EXECUTE format('ALTER TABLE %I.analysis_results ADD COLUMN IF NOT EXISTS product_int_id INTEGER', _schema);

                EXECUTE format('
                    UPDATE %I.analysis_results ar
                    SET product_int_id = p.id
                    FROM public.products p
                    WHERE p.tcg_uuid = ar.product_id
                ', _schema);

                -- Verify: rows with product_id NOT NULL but product_int_id IS NULL must be 0
                EXECUTE format('
                    SELECT COUNT(*) FROM %I.analysis_results
                    WHERE product_id IS NOT NULL AND product_int_id IS NULL
                ', _schema) INTO _bad_count;
                IF _bad_count > 0 THEN
                    RAISE EXCEPTION 'Phase B: % rows in %.analysis_results have product_id NOT NULL but product_int_id IS NULL',
                        _bad_count, _schema;
                END IF;

                -- Drop FK referencing public.products(tcg_uuid)
                SELECT conname INTO _fk_name
                FROM pg_constraint con
                JOIN pg_class c ON c.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_class fc ON fc.oid = con.confrelid
                JOIN pg_namespace fn ON fn.oid = fc.relnamespace
                WHERE n.nspname = _schema AND c.relname = 'analysis_results'
                  AND con.contype = 'f'
                  AND fn.nspname = 'public' AND fc.relname = 'products'
                LIMIT 1;
                IF _fk_name IS NOT NULL THEN
                    EXECUTE format('ALTER TABLE %I.analysis_results DROP CONSTRAINT %I', _schema, _fk_name);
                END IF;

                EXECUTE format('ALTER TABLE %I.analysis_results DROP COLUMN product_id', _schema);
                EXECUTE format('ALTER TABLE %I.analysis_results RENAME COLUMN product_int_id TO product_id', _schema);
                -- product_id stays NULLABLE for analysis_results (no SET NOT NULL)

                -- Add new FK (no CASCADE — analysis_results are soft references)
                EXECUTE format('
                    ALTER TABLE %I.analysis_results
                    ADD CONSTRAINT fk_analysis_results_product_id
                    FOREIGN KEY (product_id) REFERENCES public.products(id)
                ', _schema);

                -- Index on product_id
                EXECUTE format('
                    CREATE INDEX IF NOT EXISTS idx_%s_ar_product_id ON %I.analysis_results (product_id)
                ', _schema, _schema);

                RAISE NOTICE '  analysis_results done';
            END IF;
        ELSE
            RAISE NOTICE '  analysis_results does not exist in schema %, skip', _schema;
        END IF;

        -- ================================================================
        -- Table 5: analysis_run_snapshots  (product_id NULLABLE, only exists in some schemas)
        -- ================================================================
        IF to_regclass(format('%I.analysis_run_snapshots', _schema)) IS NOT NULL
           AND EXISTS (
               SELECT 1 FROM pg_attribute a
               JOIN pg_class c ON c.oid = a.attrelid
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = _schema
                 AND c.relname = 'analysis_run_snapshots'
                 AND a.attname = 'product_id'
                 AND a.atttypid != _int_oid
           ) THEN
            RAISE NOTICE '  Converting analysis_run_snapshots.product_id UUID->INTEGER (NULLABLE)';

            EXECUTE format('ALTER TABLE %I.analysis_run_snapshots ADD COLUMN IF NOT EXISTS product_int_id INTEGER', _schema);
            EXECUTE format('UPDATE %I.analysis_run_snapshots ars SET product_int_id = p.id FROM public.products p WHERE p.tcg_uuid = ars.product_id', _schema);
            EXECUTE format('ALTER TABLE %I.analysis_run_snapshots DROP COLUMN product_id', _schema);
            EXECUTE format('ALTER TABLE %I.analysis_run_snapshots RENAME COLUMN product_int_id TO product_id', _schema);

            RAISE NOTICE '  analysis_run_snapshots done: %.analysis_run_snapshots product_id UUID→INTEGER', _schema;
        END IF;

    END LOOP;
END;
$phase_b$;

-- ================================================================
-- product_code SEQUENCE 作成（冪等）
-- ================================================================
DO $seq$
DECLARE
    max_num INTEGER;
BEGIN
    SELECT COALESCE(MAX(CAST(SUBSTRING(product_code FROM 3) AS INTEGER)), 0)
      INTO max_num
      FROM public.products
      WHERE product_code ~ '^PM[0-9]{4}$';

    IF NOT EXISTS (
        SELECT 1 FROM pg_sequences
        WHERE schemaname = 'public' AND sequencename = 'product_code_seq'
    ) THEN
        EXECUTE format('CREATE SEQUENCE public.product_code_seq START WITH %s', max_num + 1);
        RAISE NOTICE 'Created public.product_code_seq starting at %', max_num + 1;
    ELSE
        RAISE NOTICE 'public.product_code_seq already exists, skip';
    END IF;
END;
$seq$;
