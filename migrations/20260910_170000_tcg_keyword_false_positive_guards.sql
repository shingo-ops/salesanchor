-- CARD-LINE-KEYWORD-GUARDS-01: tenant_004 only; validate all before mutation.
-- Configure timeouts before DO starts; settings expire with this transaction.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    target record;
    product record;
    keyword_count integer;
    _pid_col TEXT;
BEGIN
    -- ADR-1002: tcg_products が Phase 2c で削除済みの場合はスキップ
    IF to_regclass('tenant_004.tcg_products') IS NULL THEN
        RAISE NOTICE 'ADR-1002: tcg_products は Phase 2c で削除済み、スキップ';
        RETURN;
    END IF;

    -- Detect Phase B: product_id INTEGER → use p.id; else → use p.tcg_uuid
    IF EXISTS (
        SELECT 1 FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'tenant_004'
          AND c.relname = 'product_search_keywords'
          AND a.attname = 'product_id'
          AND a.atttypid = 23
    ) THEN
        _pid_col := 'id';
    ELSE
        _pid_col := 'tcg_uuid';
    END IF;

    SELECT count(*) INTO table_count
    FROM unnest(ARRAY['tcg_products', 'tcg_series', 'tcg_product_categories',
                      'product_search_keywords', 'product_exclude_keywords']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN
        RETURN;
    ELSIF table_count <> 5 THEN
        RAISE EXCEPTION 'tenant_004 incomplete TCG structure';
    END IF;

    LOCK TABLE public.products, tenant_004.tcg_products, tenant_004.tcg_series,
        tenant_004.tcg_product_categories, tenant_004.product_search_keywords,
        tenant_004.product_exclude_keywords IN SHARE ROW EXCLUSIVE MODE;

    FOR target IN SELECT * FROM (VALUES
        ('PM0230', 'トライアルデッキ 【推しの子】', 'IP007', 'PC_SINGLE', 'product_search_keywords', 'vol.1'),
        ('PM0104', 'ポケモンカード151', 'IP001', 'PC_BOX', 'product_exclude_keywords', 'マスターボールミラー'),
        ('PM0184', 'スターターセットMEGA メガゲンガーex', 'IP001', 'PC_BOX', 'product_exclude_keywords', 'スペシャルデッキセット')
    ) AS v(code, title, work_code, category_code, keyword_table, keyword)
    LOOP
        EXECUTE format('SELECT p.%I AS id, p.name AS japanese_title, w.code AS work_code, c.code AS category_code
        FROM public.products p
        LEFT JOIN tenant_004.tcg_series w ON w.id = p.work_id
        LEFT JOIN tenant_004.tcg_product_categories c ON c.id = p.product_category_id
        WHERE p.product_code = $1', _pid_col) INTO product USING target.code;
        IF product.id IS NULL OR product.japanese_title IS DISTINCT FROM target.title
           OR product.work_code IS DISTINCT FROM target.work_code
           OR product.category_code IS DISTINCT FROM target.category_code THEN
            RAISE EXCEPTION '% identity mismatch in tenant_004', target.code;
        END IF;
        EXECUTE format('SELECT count(*) FROM tenant_004.%I WHERE product_id=$1 AND keyword=$2', target.keyword_table)
            INTO keyword_count USING product.id, target.keyword;
        IF keyword_count > 1 THEN
            RAISE EXCEPTION '% duplicate target keyword in tenant_004', target.code;
        END IF;
    END LOOP;

    EXECUTE format('DELETE FROM tenant_004.product_search_keywords WHERE product_id = (SELECT %I FROM public.products WHERE product_code=''PM0230'') AND keyword = ''vol.1''', _pid_col);
    FOR target IN SELECT * FROM (VALUES
        ('PM0104', 'マスターボールミラー'),
        ('PM0184', 'スペシャルデッキセット')
    ) AS v(code, keyword)
    LOOP
        EXECUTE format('INSERT INTO tenant_004.product_exclude_keywords (id, product_id, keyword, position)
        SELECT gen_random_uuid(), p.%I, $1, COALESCE(MAX(e.position), -1)+1
        FROM public.products p
        LEFT JOIN tenant_004.product_exclude_keywords e ON e.product_id=p.%I
        WHERE p.product_code=$2
          AND NOT EXISTS (SELECT 1 FROM tenant_004.product_exclude_keywords existing
                          WHERE existing.product_id=p.%I AND existing.keyword=$1)
        GROUP BY p.%I', _pid_col, _pid_col, _pid_col, _pid_col)
        USING target.keyword, target.code;
    END LOOP;
END;
$body$;
COMMIT;
