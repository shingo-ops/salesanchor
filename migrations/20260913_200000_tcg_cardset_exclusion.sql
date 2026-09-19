-- CARD-LINE-CARDSET-07: one additive keyword, tenant_004 only.
-- ADR-155 準拠修正: 商品データの存在を前提としない。
-- 商品が未登録の場合はスキップ（アプリ/CSV経由で登録後に再実行で反映）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    product record;
    keyword_count integer;
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
    FROM unnest(ARRAY['tcg_series', 'tcg_product_categories',
                      'product_search_keywords', 'product_exclude_keywords']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN
        RETURN;
    ELSIF table_count <> 4 THEN
        RAISE EXCEPTION 'tenant_004 incomplete TCG structure';
    END IF;

    LOCK TABLE tenant_004.tcg_series,
        tenant_004.tcg_product_categories, tenant_004.product_search_keywords,
        tenant_004.product_exclude_keywords IN SHARE ROW EXCLUSIVE MODE;

    EXECUTE format('SELECT p.%I AS pid FROM public.products p WHERE p.product_code = $1', _pid_col) INTO product USING 'PM0263';
    IF product.pid IS NULL THEN
        RAISE NOTICE 'PM0263 not found in public.products — skipping (ADR-155: product data managed via app/CSV)';
        RETURN;
    END IF;

    SELECT count(*) INTO keyword_count
    FROM tenant_004.product_exclude_keywords
    WHERE product_id = product.pid AND keyword = 'カードセット';
    IF keyword_count > 1 THEN
        RAISE EXCEPTION 'PM0263 duplicate cardset exclusion in tenant_004';
    ELSIF keyword_count = 0 THEN
        INSERT INTO tenant_004.product_exclude_keywords (id, product_id, keyword, position)
        SELECT gen_random_uuid(), product.pid, 'カードセット', COALESCE(MAX(position), -1) + 1
        FROM tenant_004.product_exclude_keywords WHERE product_id = product.pid;
    END IF;
    -- ADR-155 Phase 3: mirror to public.product_exclude_keywords (SSOT for analyzer)
    IF to_regclass('public.product_exclude_keywords') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.product_exclude_keywords
            WHERE product_id = product.pid AND keyword = 'カードセット'
        ) THEN
            INSERT INTO public.product_exclude_keywords (product_id, keyword, position)
            SELECT product.pid, 'カードセット', COALESCE(MAX(position), -1) + 1
            FROM public.product_exclude_keywords WHERE product_id = product.pid;
        END IF;
    END IF;
END;
$body$;
COMMIT;
