-- CARD-LINE-CONDITION-NOTE-01: master-only, never rewrite extraction/results.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    condition_row record;
    old_note record;
    new_note record;
    condition_exclude text := '[サーチ済み],未サーチではない,未サーチではありません,未サーチとは限らない,未サーチ保証なし,未サーチ保証無し,サーチ済';
    note_exclude text := '伝票剥がし跡ありません,伝票剥がし跡ありではない,伝票剥がし跡ありではありません';
BEGIN
    SELECT count(*) INTO table_count
    FROM unnest(ARRAY['conditions', 'tcg_note_master']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN RETURN; END IF;
    IF table_count <> 2 THEN
        RAISE EXCEPTION 'condition note: incomplete master structure';
    END IF;
    LOCK TABLE tenant_004.conditions, tenant_004.tcg_note_master IN SHARE ROW EXCLUSIVE MODE;
    SELECT * INTO condition_row FROM tenant_004.conditions WHERE code='CN0007';
    IF condition_row.id IS NULL
       OR condition_row.canonical IS DISTINCT FROM 'Unsearched pack'
       OR condition_row.priority IS DISTINCT FROM 3 OR condition_row.is_active IS DISTINCT FROM true
       OR condition_row.app_kubun IS DISTINCT FROM ''
       OR condition_row.search_kw IS DISTINCT FROM '未サーチ,サーチなし,サーチ痕なし,サーチ痕無し,サーチ無し'
       OR condition_row.exclude_kw IS NULL
       OR condition_row.exclude_kw NOT IN ('[サーチ済み]', condition_exclude) THEN
        RAISE EXCEPTION 'condition note: CN0007 unexpected master';
    END IF;
    SELECT * INTO old_note FROM tenant_004.tcg_note_master WHERE id='NJ041';
    IF old_note.id IS NULL OR old_note.label_ja IS DISTINCT FROM '伝票跡'
       OR old_note.label_en IS DISTINCT FROM 'Shipping label marks'
       OR old_note.search_keywords IS DISTINCT FROM '伝票跡,伝票痕,伝票剥がし跡'
       OR old_note.enabled IS DISTINCT FROM true OR old_note.category IS DISTINCT FROM '跡痕系'
       OR old_note.priority IS DISTINCT FROM 1 OR old_note.match_type IS DISTINCT FROM 'LITERAL'
       OR old_note.search_pattern IS NOT NULL OR old_note.label_template IS NOT NULL
       OR old_note.exclude_keywords IS NULL
       OR old_note.exclude_keywords NOT IN ('', '伝票剥がし跡あり') THEN
        RAISE EXCEPTION 'condition note: NJ041 unexpected master';
    END IF;
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
    UPDATE tenant_004.conditions SET exclude_kw=condition_exclude
    WHERE code='CN0007' AND exclude_kw='[サーチ済み]';
    UPDATE tenant_004.tcg_note_master SET exclude_keywords='伝票剥がし跡あり'
    WHERE id='NJ041' AND exclude_keywords='';
    INSERT INTO tenant_004.tcg_note_master
        (id,label_ja,label_en,enabled,search_keywords,exclude_keywords,category,priority,match_type,search_pattern,label_template)
    VALUES ('NJ079','伝票剥がし跡あり','Shipping label removal marks',true,'伝票剥がし跡あり',note_exclude,'跡痕系',1,'STATE_LITERAL',NULL,NULL)
    ON CONFLICT (id) DO NOTHING;
END;
$body$;
COMMIT;
