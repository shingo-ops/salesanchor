-- CARD-LINE-KEYWORD-GUARDS-01: tenant_004 only; validate all before mutation.
-- A single DO statement is one transaction, including all three dictionary edits.
DO $body$
DECLARE
    table_count integer;
    target record;
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

    FOR target IN SELECT * FROM (VALUES
        ('PM0230', 'トライアルデッキ 【推しの子】', 'IP007', 'PC_SINGLE', 'product_search_keywords', 'vol.1'),
        ('PM0104', 'ポケモンカード151', 'IP001', 'PC_BOX', 'product_exclude_keywords', 'マスターボールミラー'),
        ('PM0184', 'スターターセットMEGA メガゲンガーex', 'IP001', 'PC_BOX', 'product_exclude_keywords', 'スペシャルデッキセット')
    ) AS v(code, title, work_code, category_code, keyword_table, keyword)
    LOOP
        SELECT p.id, p.japanese_title, w.code AS work_code, c.code AS category_code
        INTO product
        FROM tenant_004.tcg_products p
        LEFT JOIN tenant_004.tcg_series w ON w.id = p.work_id
        LEFT JOIN tenant_004.tcg_product_categories c ON c.id = p.product_category_id
        WHERE p.code = target.code;
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

    DELETE FROM tenant_004.product_search_keywords
    WHERE product_id = (SELECT id FROM tenant_004.tcg_products WHERE code='PM0230')
      AND keyword = 'vol.1';
    FOR target IN SELECT * FROM (VALUES
        ('PM0104', 'マスターボールミラー'),
        ('PM0184', 'スペシャルデッキセット')
    ) AS v(code, keyword)
    LOOP
        INSERT INTO tenant_004.product_exclude_keywords (id, product_id, keyword, position)
        SELECT gen_random_uuid(), p.id, target.keyword, COALESCE(MAX(e.position), -1)+1
        FROM tenant_004.tcg_products p
        LEFT JOIN tenant_004.product_exclude_keywords e ON e.product_id=p.id
        WHERE p.code=target.code
          AND NOT EXISTS (SELECT 1 FROM tenant_004.product_exclude_keywords existing
                          WHERE existing.product_id=p.id AND existing.keyword=target.keyword)
        GROUP BY p.id;
    END LOOP;
END;
$body$;
