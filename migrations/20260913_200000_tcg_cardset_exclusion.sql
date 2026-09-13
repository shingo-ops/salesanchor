-- CARD-LINE-CARDSET-07: one additive keyword, tenant_004 only.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    product record;
    keyword_count integer;
BEGIN
    SELECT count(*) INTO table_count
    FROM unnest(ARRAY['tcg_products', 'tcg_series', 'tcg_product_categories',
                      'product_search_keywords', 'product_exclude_keywords']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN
        RETURN;
    ELSIF table_count <> 5 THEN
        RAISE EXCEPTION 'tenant_004 incomplete TCG structure';
    END IF;

    LOCK TABLE tenant_004.tcg_products, tenant_004.tcg_series,
        tenant_004.tcg_product_categories, tenant_004.product_search_keywords,
        tenant_004.product_exclude_keywords IN SHARE ROW EXCLUSIVE MODE;

    SELECT p.id, p.japanese_title, p.is_active,
           w.code AS work_code, c.code AS category_code
    INTO product
    FROM tenant_004.tcg_products p
    LEFT JOIN tenant_004.tcg_series w ON w.id = p.work_id
    LEFT JOIN tenant_004.tcg_product_categories c ON c.id = p.product_category_id
    WHERE p.code = 'PM0263';
    IF product.id IS NULL
       OR product.japanese_title IS DISTINCT FROM '30th CELEBRATION'
       OR product.work_code IS DISTINCT FROM 'IP001'
       OR product.category_code IS DISTINCT FROM 'PC_BOX'
       OR product.is_active IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'PM0263 identity mismatch in tenant_004';
    END IF;

    SELECT count(*) INTO keyword_count
    FROM tenant_004.product_exclude_keywords
    WHERE product_id = product.id AND keyword = 'カードセット';
    IF keyword_count > 1 THEN
        RAISE EXCEPTION 'PM0263 duplicate cardset exclusion in tenant_004';
    ELSIF keyword_count = 0 THEN
        INSERT INTO tenant_004.product_exclude_keywords (id, product_id, keyword, position)
        SELECT gen_random_uuid(), product.id, 'カードセット', COALESCE(MAX(position), -1) + 1
        FROM tenant_004.product_exclude_keywords WHERE product_id = product.id;
    END IF;
END;
$body$;
COMMIT;
