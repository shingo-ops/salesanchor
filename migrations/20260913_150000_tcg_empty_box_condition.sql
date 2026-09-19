-- CARD-LINE-EMPTY-BOX-REVIEW-01: tenant_004 only, no historical row rewrites.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    existing record;
BEGIN
    SELECT count(*) INTO table_count
    FROM unnest(ARRAY['conditions', 'analysis_results', 'extraction_items',
                     'extraction_jobs', 'source_messages', 'item_corrections']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_schema='tenant_004'
        AND (table_name LIKE 'tcg_%' OR table_name IN (
            'analysis_run_snapshots','analysis_runs','audit_log','condition_aliases','import_jobs','item_notes',
            'product_exclude_keywords','product_search_keywords','products_logistics','supplier_channels',
            'unit_aliases','units','unparsed_lines'))
    ) THEN RETURN; END IF;
    IF table_count <> 6 THEN RAISE EXCEPTION 'empty box: incomplete TCG structure'; END IF;
    LOCK TABLE tenant_004.conditions IN SHARE ROW EXCLUSIVE MODE;
    IF (SELECT count(*) FROM tenant_004.conditions WHERE code='CN0011' OR canonical='Empty box') > 1 THEN
        RAISE EXCEPTION 'empty box: conflicting condition identities';
    END IF;
    SELECT * INTO existing FROM tenant_004.conditions WHERE code='CN0011' OR canonical='Empty box';
    IF FOUND THEN
        IF existing.code IS DISTINCT FROM 'CN0011' OR existing.canonical IS DISTINCT FROM 'Empty box'
           OR existing.priority IS DISTINCT FROM 1 OR existing.is_active IS DISTINCT FROM true
           OR existing.app_kubun IS DISTINCT FROM '' OR existing.search_kw IS DISTINCT FROM '空箱'
           OR existing.exclude_kw IS DISTINCT FROM '空箱ではない,空箱ではありません,空箱なし,空箱無し' THEN
            RAISE EXCEPTION 'empty box: unexpected existing definition';
        END IF;
        RETURN;
    END IF;
    INSERT INTO tenant_004.conditions (code, canonical, priority, app_kubun, search_kw, exclude_kw, is_active)
    VALUES ('CN0011', 'Empty box', 1, '', '空箱', '空箱ではない,空箱ではありません,空箱なし,空箱無し', true);
END;
$body$;
COMMIT;
