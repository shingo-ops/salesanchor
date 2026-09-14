-- CARD-LINE-CARDSET-08: reuse individual products; add one bundle and guards.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    refs record;
    expected record;
    product record;
    term record;
    term_count integer;
BEGIN
    IF to_regclass('public.products') IS NULL THEN RETURN; END IF;
    SELECT count(*) INTO table_count
    FROM unnest(ARRAY['tcg_major_categories', 'tcg_series',
        'tcg_manufacturers', 'tcg_product_categories',
        'product_search_keywords', 'product_exclude_keywords']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN RETURN;
    ELSIF table_count <> 6 THEN
        RAISE EXCEPTION 'cardset bundle: incomplete TCG structure';
    END IF;
    LOCK TABLE public.products, tenant_004.tcg_major_categories,
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

    FOR expected IN SELECT * FROM (VALUES
            ('PM0263', '30th CELEBRATION'),
            ('PM0264', 'FUTURISTIC BOX'),
            ('PM0265', '30th CELEBRATION プレミアムデッキセット'),
            ('PM0276', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ'),
            ('PM0277', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ'),
            ('PM0278', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ'),
            ('PM0279', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ'),
            ('PM0280', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル'),
            ('PM0281', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ'),
            ('PM0282', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット モクロー・ニャビー・アシマリ'),
            ('PM0283', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン'),
            ('PM0284', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス')
        ) AS e(code, title)
    LOOP
        SELECT tcg_uuid AS id, product_code AS code, name AS japanese_title, category_class, division_id, work_id, manufacturer_id, product_category_id, is_active INTO product FROM public.products WHERE product_code = expected.code;
        IF product.id IS NULL
           OR product.category_class IS DISTINCT FROM 'Box'
           OR product.division_id IS DISTINCT FROM refs.division_id
           OR product.work_id IS DISTINCT FROM refs.work_id
           OR product.manufacturer_id IS DISTINCT FROM refs.manufacturer_id
           OR product.product_category_id IS DISTINCT FROM refs.product_category_id
           OR product.is_active IS DISTINCT FROM true THEN
            RAISE EXCEPTION 'cardset bundle: identity mismatch %', expected.code;
        END IF;
    END LOOP;

    -- Recognize this assortment under another code instead of creating a duplicate.
    IF EXISTS (SELECT 1 FROM public.products
        WHERE product_code <> 'PM0297' AND name ILIKE '%CELEBRATION%'
          AND name LIKE '%カードセット%'
          AND name ~ '(^|[^0-9０-９])[9９][[:space:]　]*種') THEN
        RAISE EXCEPTION 'cardset bundle: assortment already exists under another code';
    END IF;
    SELECT tcg_uuid AS id, product_code AS code, name AS japanese_title, category_class, division_id, work_id, manufacturer_id, product_category_id, is_active INTO product FROM public.products WHERE product_code = 'PM0297';
    IF product.id IS NULL THEN
        INSERT INTO public.products
            (product_code, name, category_class, division_id, work_id,
             manufacturer_id, product_category_id, is_active, tcg_uuid)
        VALUES ('PM0297', 'MEGA 30th CELEBRATION カードセット（9種セット）',
            'Box', refs.division_id, refs.work_id, refs.manufacturer_id,
            refs.product_category_id, true, gen_random_uuid());
    ELSIF product.category_class IS DISTINCT FROM 'Box'
       OR product.division_id IS DISTINCT FROM refs.division_id
       OR product.work_id IS DISTINCT FROM refs.work_id
       OR product.manufacturer_id IS DISTINCT FROM refs.manufacturer_id
       OR product.product_category_id IS DISTINCT FROM refs.product_category_id
       OR product.is_active IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'cardset bundle: PM0297 code collision or identity mismatch';
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
        SELECT tcg_uuid AS id INTO product FROM public.products WHERE product_code = term.code;
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
    END LOOP;
END;
$body$;
COMMIT;
