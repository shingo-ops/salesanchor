-- CARD-LINE-CONDITION-NOTE-01: master-only, never rewrite extraction/results.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    new_note record;
    condition_exclude text := '[サーチ済み],未サーチではない,未サーチではありません,未サーチとは限らない,未サーチ保証なし,未サーチ保証無し,サーチ済';
    note_exclude text := '伝票剥がし跡ありません,伝票剥がし跡ありではない,伝票剥がし跡ありではありません';
BEGIN
    SELECT count(*) INTO table_count
    FROM unnest(ARRAY['conditions', 'tcg_note_master']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN RETURN; END IF;
    IF table_count <> 2 THEN
        RAISE NOTICE 'condition note: partial structure (% of 2 tables), skipping (SSOT migration moved to public)', table_count;
        RETURN;
    END IF;
    -- DEPRECATED: pre-UPDATE guards removed together with UPDATE statements per ADR-155
    -- Original guards verified CN0007/NJ041 state before overwriting exclude_kw/exclude_keywords
    -- Original UPDATEs set exclude_kw for CN0007 and exclude_keywords for NJ041
    -- NJ079 identity collision guard retained below (INSERT still present)
    SELECT * INTO new_note FROM tenant_004.tcg_note_master WHERE id='NJ079';
    IF new_note.id IS NOT NULL AND (
       new_note.label_ja IS DISTINCT FROM '伝票剥がし跡あり'
       OR new_note.label_en IS DISTINCT FROM 'Shipping label removal marks'
       OR new_note.enabled IS DISTINCT FROM true OR new_note.category IS DISTINCT FROM '跡痕系'
       OR new_note.priority IS DISTINCT FROM 1 OR new_note.match_type IS DISTINCT FROM 'STATE_LITERAL'
       OR new_note.search_keywords IS DISTINCT FROM '伝票剥がし跡あり'
       OR new_note.exclude_keywords IS DISTINCT FROM note_exclude
       OR new_note.search_pattern IS NOT NULL OR new_note.label_template IS NOT NULL) THEN
        RAISE EXCEPTION 'condition note: NJ079 identity collision';
    END IF;
    INSERT INTO tenant_004.tcg_note_master
        (id,label_ja,label_en,enabled,search_keywords,exclude_keywords,category,priority,match_type,search_pattern,label_template)
    VALUES ('NJ079','伝票剥がし跡あり','Shipping label removal marks',true,'伝票剥がし跡あり',note_exclude,'跡痕系',1,'STATE_LITERAL',NULL,NULL)
    ON CONFLICT (id) DO NOTHING;
END;
$body$;
COMMIT;
