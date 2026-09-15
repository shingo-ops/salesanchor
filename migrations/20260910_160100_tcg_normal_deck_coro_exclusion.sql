-- CARD-LINE-WORK-MATCHING-V3-01: preserve existing words; never register a product.
DO $body$
DECLARE
    target RECORD;
    product RECORD;
    _pid_col TEXT;
BEGIN
    FOR target IN SELECT nspname FROM pg_namespace
                  WHERE nspname LIKE 'tenant_%' ORDER BY nspname
    LOOP
        IF to_regclass(format('%I.extraction_items', target.nspname)) IS NULL
           OR to_regclass(format('%I.extraction_jobs', target.nspname)) IS NULL THEN
            CONTINUE;
        END IF;
        -- Detect Phase B: product_id INTEGER → use p.id; else → use p.tcg_uuid
        IF EXISTS (
            SELECT 1 FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = target.nspname
              AND c.relname = 'product_search_keywords'
              AND a.attname = 'product_id'
              AND a.atttypid = 23
        ) THEN
            _pid_col := 'id';
        ELSE
            _pid_col := 'tcg_uuid';
        END IF;
        EXECUTE format('SELECT p.%I AS id, p.name AS japanese_title, w.code AS work_code, p.work_id
                        FROM public.products p LEFT JOIN %I.tcg_series w ON w.id=p.work_id
                        WHERE p.product_code=''PM0200''', _pid_col, target.nspname) INTO product;
        IF product.id IS NULL THEN
            CONTINUE;
        END IF;
        IF product.work_id IS NOT NULL AND product.work_code IS NULL THEN
            CONTINUE;
        END IF;
        IF product.japanese_title IS DISTINCT FROM 'MEGA スタートデッキ100 バトルコレクション'
           OR product.work_code IS DISTINCT FROM 'IP001' THEN
            RAISE EXCEPTION 'PM0200 identity mismatch in %; no keyword inserted', target.nspname;
        END IF;
        EXECUTE format('INSERT INTO %I.product_exclude_keywords (id, product_id, keyword, position)
                        SELECT gen_random_uuid(), $1, ''コロ'', COALESCE(MAX(position), -1)+1
                        FROM %I.product_exclude_keywords
                        WHERE product_id=$1
                        HAVING NOT EXISTS (SELECT 1 FROM %I.product_exclude_keywords
                                           WHERE product_id=$1 AND keyword=''コロ'')',
                       target.nspname, target.nspname, target.nspname) USING product.id;
    END LOOP;
END;
$body$;
