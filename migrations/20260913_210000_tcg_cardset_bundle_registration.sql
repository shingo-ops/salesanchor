-- CARD-LINE-CARDSET-08: reuse individual products; add one bundle and guards.
-- ADR-155 準拠修正: 商品データの存在を前提としない。
-- 商品が未登録の場合はスキップ（アプリ/CSV経由で登録後に再実行で反映）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    refs record;
    product record;
    term record;
    term_count integer;
    _pid_col TEXT;
BEGIN
    IF to_regclass('public.products') IS NULL THEN RETURN; END IF;
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
    FROM unnest(ARRAY['tcg_major_categories', 'tcg_series',
        'tcg_manufacturers', 'tcg_product_categories',
        'product_search_keywords', 'product_exclude_keywords']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN RETURN;
    ELSIF table_count <> 6 THEN
        RAISE EXCEPTION 'cardset bundle: incomplete TCG structure';
    END IF;
    LOCK TABLE tenant_004.tcg_major_categories,
        tenant_004.tcg_series, tenant_004.tcg_manufacturers,
        tenant_004.tcg_product_categories, tenant_004.product_search_keywords,
        tenant_004.product_exclude_keywords IN SHARE ROW EXCLUSIVE MODE;

    SELECT d.id AS division_id, w.id AS work_id, m.id AS manufacturer_id,
           c.id AS product_category_id INTO refs
    FROM tenant_004.tcg_major_categories d, tenant_004.tcg_series w,
         tenant_004.tcg_manufacturers m, tenant_004.tcg_product_categories c
    WHERE d.code = 'DIV01' AND w.code = 'IP001' AND m.code = 'MK001'
      AND c.code = 'PC_BOX' AND c.kubun_type = '箱系'
      AND d.is_active AND w.is_active AND m.is_active AND c.is_active;
    IF refs.division_id IS NULL THEN
        RAISE EXCEPTION 'cardset bundle: reference missing or inactive';
    END IF;

    FOR term IN SELECT * FROM (VALUES
        ('PM0263', 'カードセット', 'product_exclude_keywords'),
        ('PM0264', 'カードセット', 'product_exclude_keywords'),
        ('PM0265', 'カードセット', 'product_exclude_keywords'),
        ('PM0276', '種セット', 'product_exclude_keywords'),
        ('PM0277', '種セット', 'product_exclude_keywords'),
        ('PM0278', '種セット', 'product_exclude_keywords'),
        ('PM0279', '種セット', 'product_exclude_keywords'),
        ('PM0280', '種セット', 'product_exclude_keywords'),
        ('PM0281', '種セット', 'product_exclude_keywords'),
        ('PM0282', '種セット', 'product_exclude_keywords'),
        ('PM0283', '種セット', 'product_exclude_keywords'),
        ('PM0284', '種セット', 'product_exclude_keywords'),
        ('PM0297', 'FUTURISTIC', 'product_exclude_keywords'),
        ('PM0297', 'プレミアムデッキセット', 'product_exclude_keywords'),
        ('PM0297', '30th CELEBRATION カードセット (9種セット)', 'product_search_keywords')
    ) AS k(code, keyword, table_name)
    LOOP
        EXECUTE format('SELECT %I AS id FROM public.products WHERE product_code = $1', _pid_col) INTO product USING term.code;
        IF product.id IS NULL THEN
            RAISE NOTICE 'cardset bundle: % not found — skipping keyword (ADR-155)', term.code;
            CONTINUE;
        END IF;
        EXECUTE format('SELECT count(*) FROM tenant_004.%I WHERE product_id=$1 AND keyword=$2', term.table_name)
            INTO term_count USING product.id, term.keyword;
        IF term_count > 1 THEN
            RAISE EXCEPTION 'cardset bundle: duplicate keyword % %', term.code, term.keyword;
        ELSIF term_count = 0 THEN
            EXECUTE format('INSERT INTO tenant_004.%I (id, product_id, keyword, position)
                SELECT gen_random_uuid(), $1, $2, COALESCE(MAX(position), -1) + 1
                FROM tenant_004.%I WHERE product_id=$1', term.table_name, term.table_name)
                USING product.id, term.keyword;
        END IF;
        -- ADR-155 Phase 3: mirror to public keyword tables (SSOT for analyzer)
        IF term.table_name = 'product_exclude_keywords'
           AND to_regclass('public.product_exclude_keywords') IS NOT NULL THEN
            IF NOT EXISTS (
                SELECT 1 FROM public.product_exclude_keywords
                WHERE product_id = product.id AND keyword = term.keyword
            ) THEN
                INSERT INTO public.product_exclude_keywords (product_id, keyword, position)
                SELECT product.id, term.keyword, COALESCE(MAX(position), -1) + 1
                FROM public.product_exclude_keywords WHERE product_id = product.id;
            END IF;
        ELSIF term.table_name = 'product_search_keywords'
              AND to_regclass('public.product_search_keywords') IS NOT NULL THEN
            IF NOT EXISTS (
                SELECT 1 FROM public.product_search_keywords
                WHERE product_id = product.id AND keyword = term.keyword
            ) THEN
                INSERT INTO public.product_search_keywords (product_id, keyword, position)
                SELECT product.id, term.keyword, COALESCE(MAX(position), -1) + 1
                FROM public.product_search_keywords WHERE product_id = product.id;
            END IF;
        END IF;
    END LOOP;
END;
$body$;
COMMIT;
