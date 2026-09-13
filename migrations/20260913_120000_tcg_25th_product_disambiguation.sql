-- CARD-LINE-25TH-MASTER-01 / design-keyword §17 revision 4.
-- Additive tenant_004 dictionary change; every guard precedes the first INSERT.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    required_tables text[] := ARRAY['tcg_products','product_search_keywords','product_exclude_keywords',
        'tcg_major_categories','tcg_series','tcg_manufacturers','tcg_product_categories'];
    table_count integer;
    base record;
    candidate record;
    candidate_ids uuid[];
    set_id uuid;
    next_number integer;
    new_code text;
    word text;
    target_id uuid;
    target_table text;
    target_words text[];
    actual_words text[];
    baseline_words text[];
    set_search text[] := ARRAY['25thアニバーサリー スペシャルセット','25th ANNIVERSARY COLLECTION スペシャルセット'];
    set_exclude text[] := ARRAY['サプライのみ','スペシャルセットではない','スペシャルセットではありません','スペシャルセットじゃない','スペシャルセットでは無い'];
    base_exclude text[] := ARRAY['プロモ','ゴールデン','golden','サプライのみ','スペシャルセット'];
BEGIN
    SELECT count(*) INTO table_count FROM unnest(required_tables) t
    WHERE to_regclass('tenant_004.' || t) IS NOT NULL;
    IF table_count = 0 AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_schema='tenant_004'
        AND (table_name LIKE 'tcg_%' OR table_name IN (
            'conditions','analysis_results','extraction_items','extraction_jobs','source_messages','item_corrections',
            'analysis_run_snapshots','analysis_runs','audit_log','condition_aliases','import_jobs','item_notes',
            'products_logistics','supplier_channels','unit_aliases','units','unparsed_lines'))
    ) THEN RETURN; END IF;
    IF table_count <> cardinality(required_tables) THEN
        RAISE EXCEPTION '25th partial tables; no changes';
    END IF;
    LOCK TABLE tenant_004.tcg_products, tenant_004.product_search_keywords,
        tenant_004.product_exclude_keywords IN SHARE ROW EXCLUSIVE MODE;
    LOCK TABLE tenant_004.tcg_major_categories, tenant_004.tcg_series,
        tenant_004.tcg_manufacturers, tenant_004.tcg_product_categories IN SHARE MODE;
    SELECT p.* INTO base FROM tenant_004.tcg_products p
    JOIN tenant_004.tcg_major_categories d ON d.id=p.division_id AND d.code='DIV01' AND d.display_name='TCG' AND d.is_active
    JOIN tenant_004.tcg_series w ON w.id=p.work_id AND w.code='IP001' AND w.display_name='Pokemon' AND w.is_active
    JOIN tenant_004.tcg_manufacturers m ON m.id=p.manufacturer_id AND m.code='MK001' AND m.display_name='The Pokemon Company' AND m.is_active
    JOIN tenant_004.tcg_product_categories c ON c.id=p.product_category_id AND c.code='PC_BOX' AND c.display_name='Box' AND c.kubun_type='箱系' AND c.is_active
    WHERE p.id='797f6adb-87f5-4316-99be-6227bda5c431'::uuid AND p.code='PM0071'
      AND p.japanese_title='25th Anniversary Collection' AND p.mark='S8a' AND p.is_active;
    IF base.id IS NULL THEN RAISE EXCEPTION '25th base identity mismatch'; END IF;
    IF EXISTS (SELECT 1 FROM tenant_004.product_search_keywords GROUP BY product_id,keyword HAVING count(*)>1)
       OR EXISTS (SELECT 1 FROM tenant_004.product_exclude_keywords GROUP BY product_id,keyword HAVING count(*)>1) THEN
        RAISE EXCEPTION '25th duplicate existing keyword';
    END IF;
    -- Verify the recorded base dictionary; additions from this migration are allowed on replay.
    FOREACH target_table IN ARRAY ARRAY['product_search_keywords','product_exclude_keywords'] LOOP
        IF target_table='product_search_keywords' THEN
            baseline_words := ARRAY['25th Anniversary Collection','25thANNIVERSARYCOLLECTION'];
            target_words := ARRAY['25thアニバーサリー'];
        ELSE
            baseline_words := ARRAY['25th Aniniversary Golden Box','25th Anniversary Collection プロモパック','25th Anniversary Collection プロモ','プロモパック'];
            target_words := base_exclude;
        END IF;
        EXECUTE format('SELECT array_agg(keyword) FROM tenant_004.%I WHERE product_id=$1',target_table) INTO actual_words USING base.id;
        IF NOT baseline_words <@ COALESCE(actual_words,ARRAY[]::text[])
           OR NOT COALESCE(actual_words,ARRAY[]::text[]) <@ (baseline_words || target_words) THEN
            RAISE EXCEPTION '25th unexpected base dictionary: %',target_table;
        END IF;
    END LOOP;
    SELECT array_agg(p.id) INTO candidate_ids FROM tenant_004.tcg_products p
    WHERE (lower(p.japanese_title) LIKE '%25th%' AND p.japanese_title LIKE '%スペシャルセット%')
       OR EXISTS (SELECT 1 FROM tenant_004.product_search_keywords k WHERE k.product_id=p.id
                  AND (lower(k.keyword) LIKE '%25th%' AND k.keyword LIKE '%スペシャルセット%'));
    IF cardinality(candidate_ids)>1 THEN RAISE EXCEPTION '25th multiple set candidates'; END IF;
    IF cardinality(candidate_ids)=1 THEN
        SELECT * INTO candidate FROM tenant_004.tcg_products WHERE id=candidate_ids[1];
        IF candidate.japanese_title IS DISTINCT FROM '25th ANNIVERSARY COLLECTION スペシャルセット'
           OR candidate.release_date IS DISTINCT FROM DATE '2021-10-22'
           OR candidate.is_active IS DISTINCT FROM true OR candidate.category_class IS DISTINCT FROM 'Pokemon'
           OR candidate.division_id IS DISTINCT FROM base.division_id OR candidate.work_id IS DISTINCT FROM base.work_id
           OR candidate.manufacturer_id IS DISTINCT FROM base.manufacturer_id
           OR candidate.product_category_id IS DISTINCT FROM base.product_category_id
           OR candidate.mark IS NOT NULL OR candidate.english_title IS NOT NULL OR candidate.required_output_value IS NOT NULL
           OR candidate.code !~ '^PM[0-9]{4}$' THEN
            RAISE EXCEPTION '25th set identity mismatch';
        END IF;
        set_id := candidate.id;
        FOREACH target_table IN ARRAY ARRAY['product_search_keywords','product_exclude_keywords'] LOOP
            target_words := CASE WHEN target_table='product_search_keywords' THEN set_search ELSE set_exclude END;
            EXECUTE format('SELECT array_agg(keyword) FROM tenant_004.%I WHERE product_id=$1',target_table) INTO actual_words USING set_id;
            IF NOT COALESCE(actual_words,ARRAY[]::text[]) @> target_words
               OR NOT COALESCE(actual_words,ARRAY[]::text[]) <@ target_words THEN
                RAISE EXCEPTION '25th set dictionary mismatch';
            END IF;
        END LOOP;
    ELSE
        SELECT COALESCE(max(substring(code FROM 3)::integer),0)+1 INTO next_number
        FROM tenant_004.tcg_products WHERE code ~ '^PM[0-9]{4}$';
        IF next_number>9999 THEN RAISE EXCEPTION '25th PM code exhausted'; END IF;
        new_code := 'PM' || lpad(next_number::text,4,'0');
        IF EXISTS (SELECT 1 FROM tenant_004.tcg_products WHERE code=new_code) THEN
            RAISE EXCEPTION '25th PM code conflict';
        END IF;
    END IF;
    -- All read/identity/word checks completed. UUID uses the existing column default.
    IF set_id IS NULL THEN
        INSERT INTO tenant_004.tcg_products
            (code,japanese_title,release_date,category_class,division_id,work_id,manufacturer_id,product_category_id,is_active,mark,english_title,required_output_value)
        VALUES (new_code,'25th ANNIVERSARY COLLECTION スペシャルセット',DATE '2021-10-22','Pokemon',
                base.division_id,base.work_id,base.manufacturer_id,base.product_category_id,true,NULL,NULL,NULL)
        RETURNING id INTO set_id;
    END IF;
    FOREACH target_id IN ARRAY ARRAY[base.id,set_id] LOOP
        FOREACH target_table IN ARRAY ARRAY['product_search_keywords','product_exclude_keywords'] LOOP
            target_words := CASE WHEN target_id=base.id THEN
                CASE WHEN target_table='product_search_keywords' THEN ARRAY['25thアニバーサリー'] ELSE base_exclude END
                ELSE CASE WHEN target_table='product_search_keywords' THEN set_search ELSE set_exclude END END;
            FOREACH word IN ARRAY target_words LOOP
                EXECUTE format('INSERT INTO tenant_004.%I (product_id,keyword,position)
                    SELECT $1,$2,COALESCE(max(position),-1)+1 FROM tenant_004.%I WHERE product_id=$1
                    HAVING NOT EXISTS (SELECT 1 FROM tenant_004.%I WHERE product_id=$1 AND keyword=$2)',
                    target_table,target_table,target_table) USING target_id,word;
            END LOOP;
        END LOOP;
    END LOOP;
END;
$body$;
COMMIT;
