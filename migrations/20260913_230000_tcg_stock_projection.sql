-- Additive stock projection storage; repeat after provisioning new TCG tenants.
-- The DO statement is one transaction. A partially provisioned TCG tenant fails it.
DO $migration$
DECLARE
    ns text;
    parent_name text;
    parents text[] := ARRAY['supplier_channels','tcg_products','units','conditions',
        'source_messages','extraction_jobs','extraction_items','tcg_distribution_targets'];
    present_count integer;
    relation_name text;
    column_name text;
    saved_path text := current_setting('search_path');
BEGIN
    FOR ns IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]{3}$' ORDER BY nspname
    LOOP
        present_count := 0;
        FOREACH parent_name IN ARRAY parents LOOP
            IF to_regclass(format('%I.%I',ns,parent_name)) IS NOT NULL THEN
                present_count := present_count + 1;
            END IF;
        END LOOP;
        IF present_count = 0 THEN CONTINUE; END IF;
        IF present_count <> cardinality(parents) THEN
            RAISE EXCEPTION 'stock projection: incomplete TCG parents in %',ns;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns c WHERE c.table_schema=ns
                      AND c.table_name='source_messages' AND c.column_name='line_posted_at') THEN
            RAISE EXCEPTION 'stock projection: line_posted_at prerequisite missing in %',ns;
        END IF;
        PERFORM set_config('search_path',format('%I,pg_catalog',ns),true);
        EXECUTE $ddl$
CREATE OR REPLACE FUNCTION stock_keys(v jsonb, expected text[]) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path FROM CURRENT AS $fn$
    SELECT coalesce(jsonb_typeof(v)='object' AND v ?& expected
                    AND v - expected = '{}'::jsonb,false)
$fn$;
CREATE OR REPLACE FUNCTION stock_scalar(v jsonb, kind text, nullable boolean DEFAULT false) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE t text; n numeric; d timestamptz;
BEGIN
    IF v IS NULL THEN RETURN false; END IF;
    IF v='null'::jsonb THEN RETURN nullable; END IF;
    t := v #>> '{}';
    CASE kind
    WHEN 'string' THEN RETURN jsonb_typeof(v)='string';
    WHEN 'nonempty' THEN RETURN jsonb_typeof(v)='string' AND length(t)>0;
    WHEN 'boolean' THEN RETURN jsonb_typeof(v)='boolean';
    WHEN 'uuid' THEN RETURN jsonb_typeof(v)='string' AND t ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
    WHEN 'digest' THEN RETURN jsonb_typeof(v)='string' AND t ~ '^[0-9a-f]{64}$';
    WHEN 'decimal' THEN
        IF jsonb_typeof(v)<>'string' OR t !~ '^[0-9]+([.][0-9]{1,2})?$' THEN RETURN false; END IF;
        n := t::numeric; RETURN n BETWEEN 0 AND 999999999999.99;
    WHEN 'integer' THEN
        IF jsonb_typeof(v)<>'number' OR t !~ '^[0-9]+$' THEN RETURN false; END IF;
        RETURN t::numeric BETWEEN 0 AND 9223372036854775807;
    WHEN 'positive' THEN RETURN stock_scalar(v,'integer') AND t::numeric>0;
    WHEN 'date' THEN
        IF jsonb_typeof(v)<>'string' OR t !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN RETURN false; END IF;
        RETURN isfinite(t::date);
    WHEN 'timestamp' THEN
        IF jsonb_typeof(v)<>'string' OR t !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]{1,6})?Z$'
        THEN RETURN false; END IF;
        d := t::timestamptz; RETURN isfinite(d) AND substring(t,12,2)::int<24 AND substring(t,18,2)::int<60;
    ELSE RETURN false;
    END CASE;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range OR datetime_field_overflow THEN
    RETURN false;
END $fn$;
CREATE OR REPLACE FUNCTION stock_array(v jsonb, kind text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE e jsonb; previous text; previous_number numeric := 0; seen jsonb := '[]'; t text;
BEGIN
    IF jsonb_typeof(v) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
    FOR e IN SELECT value FROM jsonb_array_elements(v) LOOP
        t := e #>> '{}';
        IF kind='corrections' THEN
            IF jsonb_typeof(e)<>'string' OR t !~ '^[1-9][0-9]*$' THEN RETURN false; END IF;
            IF t::numeric>9223372036854775807 OR t::numeric<=previous_number THEN RETURN false; END IF;
            previous_number := t::numeric;
        ELSE
            IF NOT stock_scalar(e,CASE WHEN kind IN ('uuid','event_ids') THEN 'uuid' ELSE 'nonempty' END) THEN RETURN false; END IF;
            IF seen @> jsonb_build_array(e) THEN RETURN false; END IF;
            IF kind='uuid' AND previous IS NOT NULL AND t<=previous COLLATE "C" THEN RETURN false; END IF;
            previous := t; seen := seen || jsonb_build_array(e);
        END IF;
    END LOOP;
    RETURN true;
END $fn$;
CREATE OR REPLACE FUNCTION stock_evidence_shape(v jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE k text;
BEGIN
    IF NOT stock_keys(v,ARRAY['format_version','field_evidence','shipping','clauses'])
        OR v->'format_version'<>'5'::jsonb OR NOT stock_scalar(v->'format_version','integer')
        OR NOT stock_keys(v->'field_evidence',ARRAY['raw_product_name','raw_quantity','raw_price','raw_unit','raw_state','raw_memo','raw_work_name'])
        OR NOT stock_keys(v->'shipping',ARRAY['label','evidence'])
        OR NOT stock_scalar(v->'shipping'->'label','string')
        OR jsonb_typeof(v->'shipping'->'evidence') IS DISTINCT FROM 'array'
        OR jsonb_typeof(v->'clauses') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
    FOR k IN SELECT jsonb_object_keys(v->'field_evidence') LOOP
        IF jsonb_typeof(v->'field_evidence'->k) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
    END LOOP;
    RETURN true;
END $fn$;
CREATE OR REPLACE FUNCTION stock_selector(v jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE k text;
BEGIN
    IF NOT stock_keys(v,ARRAY['channel_id','product_id','unit_id','condition_id','price','shipping_label','evidence'])
        OR NOT stock_scalar(v->'channel_id','uuid') OR NOT stock_scalar(v->'price','decimal',true)
        OR NOT stock_scalar(v->'shipping_label','string',true)
        OR NOT stock_keys(v->'evidence',ARRAY['product_id','unit_id','condition_id','price','shipping_label']) THEN RETURN false; END IF;
    FOREACH k IN ARRAY ARRAY['product_id','unit_id','condition_id'] LOOP
        IF NOT stock_scalar(v->k,'uuid',true) THEN RETURN false; END IF;
    END LOOP;
    FOR k IN SELECT jsonb_object_keys(v->'evidence') LOOP
        IF jsonb_typeof(v->'evidence'->k) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
    END LOOP;
    RETURN true;
END $fn$;
CREATE OR REPLACE FUNCTION stock_analysis(v jsonb, result_snapshot boolean) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE k text; p jsonb;
BEGIN
    IF NOT result_snapshot THEN
        IF NOT stock_keys(v,ARRAY['schema_version','engine_version','prompt_version','policy_version','work_reference_sha256','source_sha256','extraction_payload','correction_ids'])
            OR v->'schema_version'<>'1'::jsonb OR NOT stock_scalar(v->'schema_version','integer')
            OR NOT stock_scalar(v->'work_reference_sha256','digest',true)
            OR NOT stock_scalar(v->'source_sha256','digest') THEN RETURN false; END IF;
        FOREACH k IN ARRAY ARRAY['engine_version','prompt_version','policy_version'] LOOP
            IF NOT stock_scalar(v->k,'string') THEN RETURN false; END IF;
        END LOOP;
        p := v->'extraction_payload';
        IF p<>'null'::jsonb THEN
            IF NOT stock_keys(p,ARRAY['raw_product_name','raw_quantity','raw_price','raw_unit','raw_state','raw_memo','raw_work_name','resolved_work_id','line_start','line_end','evidence_payload']) THEN RETURN false; END IF;
            FOREACH k IN ARRAY ARRAY['raw_product_name','raw_quantity','raw_price','raw_unit','raw_state','raw_memo','raw_work_name'] LOOP
                IF NOT stock_scalar(p->k,'string') THEN RETURN false; END IF;
            END LOOP;
            IF NOT stock_scalar(p->'resolved_work_id','uuid',true) OR NOT stock_scalar(p->'line_start','positive')
                OR NOT stock_scalar(p->'line_end','positive') OR (p->>'line_start')::bigint>(p->>'line_end')::bigint
                OR NOT stock_evidence_shape(p->'evidence_payload') THEN RETURN false; END IF;
        END IF;
    ELSE
        IF NOT stock_keys(v,ARRAY['schema_version','kind','extraction_item_id','product_id','unit_id','condition_id','quantity','price','status','exclusion','pid_resolved','unit_resolved','needs_review','pid_basis','unit_basis','condition_basis','review_reasons','evidence','correction_ids','proposal'])
            OR v->'schema_version'<>'1'::jsonb OR NOT stock_scalar(v->'schema_version','integer')
            OR NOT coalesce(v->>'kind' IN ('item','no_item'),false) OR NOT stock_array(v->'review_reasons','reasons')
            OR jsonb_typeof(v->'evidence') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
        FOREACH k IN ARRAY ARRAY['extraction_item_id','product_id','unit_id','condition_id'] LOOP
            IF NOT stock_scalar(v->k,'uuid',true) THEN RETURN false; END IF;
        END LOOP;
        FOREACH k IN ARRAY ARRAY['quantity','price'] LOOP
            IF NOT stock_scalar(v->k,'decimal',true) THEN RETURN false; END IF;
        END LOOP;
        FOREACH k IN ARRAY ARRAY['status','exclusion','pid_basis','unit_basis','condition_basis'] LOOP
            IF NOT stock_scalar(v->k,'string',true) THEN RETURN false; END IF;
        END LOOP;
        FOREACH k IN ARRAY ARRAY['pid_resolved','unit_resolved','needs_review'] LOOP
            IF NOT stock_scalar(v->k,'boolean') THEN RETURN false; END IF;
        END LOOP;
        IF v->>'kind'='no_item' THEN
            FOREACH k IN ARRAY ARRAY['extraction_item_id','product_id','unit_id','condition_id','quantity','price','pid_basis','unit_basis','condition_basis'] LOOP
                IF v->k<>'null'::jsonb THEN RETURN false; END IF;
            END LOOP;
            IF v->'pid_resolved'<>'false'::jsonb OR v->'unit_resolved'<>'false'::jsonb THEN RETURN false; END IF;
        END IF;
        p := v->'proposal';
        IF NOT stock_keys(p,ARRAY['event_kind','target_selector','patch','review_reasons'])
            OR NOT coalesce(p->>'event_kind' IN ('stock_set','sold_out','offer_patch','plan_assert','plan_deny','ignore'),false)
            OR NOT stock_selector(p->'target_selector') OR jsonb_typeof(p->'patch') IS DISTINCT FROM 'object'
            OR NOT stock_array(p->'review_reasons','reasons') THEN RETURN false; END IF;
    END IF;
    RETURN stock_array(v->'correction_ids','corrections');
END $fn$;
CREATE TABLE IF NOT EXISTS tcg_stock_offers (
    id uuid PRIMARY KEY, supplier_channel_id uuid NOT NULL REFERENCES supplier_channels(id) ON DELETE RESTRICT,
    product_id uuid NOT NULL REFERENCES tcg_products(id) ON DELETE RESTRICT,
    unit_id uuid NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    condition_id uuid NOT NULL REFERENCES conditions(id) ON DELETE RESTRICT,
    price numeric(14,2), shipping_label text, shipping_evidence jsonb NOT NULL CHECK(jsonb_typeof(shipping_evidence)='array'),
    quantity numeric(14,2), availability text NOT NULL CHECK(availability IN ('available','sold_out','unknown')),
    quantity_event_id uuid, price_event_id uuid, condition_event_id uuid, validation_event_id uuid,
    revision bigint NOT NULL DEFAULT 1 CHECK(revision>=1),
    created_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(created_at)),
    updated_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(updated_at)),
    CHECK(price IS NULL OR price BETWEEN 0 AND 999999999999.99),
    CHECK(quantity IS NULL OR quantity BETWEEN 0 AND 999999999999.99),
    CHECK((availability='available' AND quantity IS NOT NULL AND quantity>0)
        OR (availability='sold_out' AND quantity IS NOT NULL AND quantity=0)
        OR (availability='unknown' AND quantity IS NULL))
);
CREATE TABLE IF NOT EXISTS tcg_stock_events (
    id uuid PRIMARY KEY, source_message_id uuid NOT NULL REFERENCES source_messages(id) ON DELETE RESTRICT,
    extraction_item_id uuid REFERENCES extraction_items(id) ON DELETE RESTRICT,
    offer_id uuid REFERENCES tcg_stock_offers(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    event_kind text NOT NULL CHECK(event_kind IN ('stock_set','sold_out','offer_patch','plan_assert','plan_deny','ignore')),
    event_key text NOT NULL UNIQUE, engine_version text NOT NULL,
    source_posted_at timestamptz CHECK(source_posted_at IS NULL OR isfinite(source_posted_at)),
    evidence jsonb NOT NULL CHECK(jsonb_typeof(evidence)='object'), patch jsonb NOT NULL CHECK(jsonb_typeof(patch)='object'),
    decision text NOT NULL CHECK(decision IN ('pending','applied','ignored','stale','rejected')),
    review_reasons jsonb NOT NULL CHECK(stock_array(review_reasons,'reasons')),
    before_values jsonb NOT NULL, after_values jsonb NOT NULL, applied_offer_revision bigint CHECK(applied_offer_revision>=1),
    analysis_input_snapshot jsonb NOT NULL CHECK(stock_analysis(analysis_input_snapshot,false)),
    analysis_result_snapshot jsonb NOT NULL CHECK(stock_analysis(analysis_result_snapshot,true)),
    analysis_input_digest text NOT NULL CHECK(analysis_input_digest ~ '^[0-9a-f]{64}$'),
    analysis_result_digest text NOT NULL CHECK(analysis_result_digest ~ '^[0-9a-f]{64}$'),
    proposal_input_digest text NOT NULL CHECK(proposal_input_digest ~ '^[0-9a-f]{64}$'),
    supersedes_event_id uuid REFERENCES tcg_stock_events(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    resolution_key text UNIQUE, resolution_request_hash text CHECK(resolution_request_hash ~ '^[0-9a-f]{64}$'),
    resolved_by text, resolved_at timestamptz CHECK(resolved_at IS NULL OR isfinite(resolved_at)), resolution_response jsonb,
    created_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(created_at)),
    applied_at timestamptz CHECK(applied_at IS NULL OR isfinite(applied_at)),
    CHECK(num_nonnulls(resolution_key,resolution_request_hash,resolved_by,resolved_at,resolution_response) IN (0,5)),
    CHECK(resolution_response IS NULL OR stock_keys(resolution_response,ARRAY['event_id','decision','offer_id','applied_offer_revision','reason','reconciliation'])),
    CHECK((decision='applied' AND offer_id IS NOT NULL AND applied_at IS NOT NULL AND applied_offer_revision IS NOT NULL AND event_kind<>'ignore')
        OR (decision<>'applied' AND applied_at IS NULL AND applied_offer_revision IS NULL)),
    CHECK(stock_keys(before_values,ARRAY['offer','plans','validated_inputs'])),
    CHECK(stock_keys(after_values,ARRAY['offer','plans','validated_inputs']))
);
CREATE TABLE IF NOT EXISTS tcg_restock_plans (
    id uuid PRIMARY KEY, offer_id uuid NOT NULL REFERENCES tcg_stock_offers(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    polarity text NOT NULL CHECK(polarity IN ('positive','negative','unknown')), certainty_raw text NOT NULL,
    date_kind text NOT NULL CHECK(date_kind IN ('arrival','shipment','order_cutoff','unknown')),
    date_precision text NOT NULL CHECK(date_precision IN ('day','range','period','unspecified')), date_raw text NOT NULL,
    date_start date CHECK(date_start IS NULL OR isfinite(date_start)), date_end date CHECK(date_end IS NULL OR isfinite(date_end)),
    resolution text NOT NULL CHECK(resolution IN ('resolved','unspecified','needs_review')), review_reason text,
    source_event_id uuid NOT NULL REFERENCES tcg_stock_events(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    revision bigint NOT NULL DEFAULT 1 CHECK(revision>=1),
    created_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(created_at)), updated_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(updated_at)),
    CHECK(date_precision<>'period' OR date_raw<>''),
    CHECK((resolution='resolved' AND review_reason IS NULL AND date_start IS NOT NULL AND date_end IS NOT NULL
        AND ((date_precision='day' AND date_start=date_end) OR (date_precision='range' AND date_start<=date_end)))
        OR (resolution='unspecified' AND date_precision IN ('unspecified','period') AND date_start IS NULL AND date_end IS NULL AND review_reason IS NULL)
        OR (resolution='needs_review' AND date_start IS NULL AND date_end IS NULL AND review_reason IS NOT NULL AND review_reason<>''))
);
CREATE TABLE IF NOT EXISTS tcg_stock_publications (
    id uuid PRIMARY KEY, state text NOT NULL CHECK(state IN ('building','ready','delivering','completed','partial','failed')),
    schema_version integer NOT NULL CHECK(schema_version>=1), input_manifest jsonb NOT NULL, rows jsonb NOT NULL,
    rows_sha256 text CHECK(rows_sha256 ~ '^[0-9a-f]{64}$'), row_count integer NOT NULL CHECK(row_count>=0),
    target_results jsonb NOT NULL CHECK(jsonb_typeof(target_results)='object'),
    created_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(created_at)), ready_at timestamptz CHECK(ready_at IS NULL OR isfinite(ready_at)),
    CHECK(state NOT IN ('ready','delivering','completed','partial') OR (rows_sha256 IS NOT NULL AND ready_at IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS tcg_stock_control (
    id smallint PRIMARY KEY CHECK(id=1), rollout_id uuid NOT NULL UNIQUE,
    mode text NOT NULL CHECK(mode IN ('legacy','shadow','paused','projected')),
    resume_mode text CHECK(resume_mode IN ('legacy','shadow','projected')),
    revision bigint NOT NULL DEFAULT 1 CHECK(revision>=1), next_seq bigint NOT NULL DEFAULT 1 CHECK(next_seq>=1),
    watermark_seq bigint CHECK(watermark_seq>=0 AND watermark_seq<next_seq),
    baseline_publication_id uuid REFERENCES tcg_stock_publications(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    approved_publication_id uuid REFERENCES tcg_stock_publications(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    last_reason text, updated_by text,
    created_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(created_at)), updated_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(updated_at)),
    CHECK((mode='paused')=(resume_mode IS NOT NULL)),
    CHECK(NOT (mode IN ('shadow','projected') OR (mode='paused' AND resume_mode IN ('shadow','projected'))) OR baseline_publication_id IS NOT NULL),
    CHECK(NOT (mode='projected' OR (mode='paused' AND resume_mode='projected')) OR approved_publication_id IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS tcg_stock_inbox (
    source_message_id uuid PRIMARY KEY REFERENCES source_messages(id) ON DELETE RESTRICT,
    seq bigint NOT NULL UNIQUE CHECK(seq>=1), state text NOT NULL CHECK(state IN ('pending','settled','error')),
    event_ids jsonb NOT NULL CHECK(stock_array(event_ids,'event_ids')), error_code text,
    attempt_count integer NOT NULL DEFAULT 0 CHECK(attempt_count>=0),
    created_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(created_at)), updated_at timestamptz NOT NULL DEFAULT now() CHECK(isfinite(updated_at)),
    CHECK(state<>'error' OR error_code IS NOT NULL), CHECK(state<>'settled' OR jsonb_array_length(event_ids)>0)
);
ALTER TABLE extraction_items ADD COLUMN IF NOT EXISTS evidence_payload jsonb;
ALTER TABLE tcg_distribution_targets ADD COLUMN IF NOT EXISTS active_publication_id uuid;
$ddl$;
        -- Remaining referential and transition guards follow in this same transaction.
        EXECUTE $ddl$
CREATE OR REPLACE FUNCTION stock_target(v jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE k text;
BEGIN
    IF NOT stock_keys(v,ARRAY['id','name','spreadsheet_id','sheet_name','sa_key_secret_name','is_active'])
        OR NOT stock_scalar(v->'id','uuid') OR NOT stock_scalar(v->'is_active','boolean') THEN RETURN false; END IF;
    FOREACH k IN ARRAY ARRAY['name','spreadsheet_id','sheet_name','sa_key_secret_name'] LOOP
        IF NOT stock_scalar(v->k,'string') THEN RETURN false; END IF;
    END LOOP;
    RETURN true;
END $fn$;
CREATE OR REPLACE FUNCTION stock_target_value(t tcg_distribution_targets) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path FROM CURRENT AS $fn$
    SELECT jsonb_build_object('id',t.id,'name',t.name,'spreadsheet_id',t.spreadsheet_id,
        'sheet_name',t.sheet_name,'sa_key_secret_name',t.sa_key_secret_name,'is_active',t.is_active)
$fn$;
CREATE OR REPLACE FUNCTION stock_publication_shape(p tcg_stock_publications) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE m jsonb := p.input_manifest; k text; v jsonb; r jsonb; a jsonb; last_a jsonb;
    ids jsonb := '[]'; keys_seen jsonb; requests jsonb := '{}'; previous text;
    count_success integer := 0; count_failed integer := 0; count_reserved integer := 0;
    count_targets integer := 0; cells jsonb; field_name text;
BEGIN
    IF NOT stock_keys(m,ARRAY['schema_version','kind','rollout_id','control_revision','watermark_seq','source_ids','offer_revisions','target_snapshots','validation','baseline_publication_id'])
        OR m->'schema_version'<>'1'::jsonb OR NOT stock_scalar(m->'schema_version','integer')
        OR NOT coalesce(m->>'kind' IN ('baseline','cutover','stock','legacy_stock'),false)
        OR NOT stock_scalar(m->'rollout_id','uuid') OR NOT stock_scalar(m->'control_revision','positive')
        OR NOT stock_scalar(m->'watermark_seq','integer',true) OR NOT stock_scalar(m->'baseline_publication_id','uuid',true)
        OR NOT stock_array(m->'source_ids','uuid') OR jsonb_typeof(m->'offer_revisions') IS DISTINCT FROM 'array'
        OR jsonb_typeof(m->'target_snapshots') IS DISTINCT FROM 'object'
        OR NOT stock_keys(m->'validation',ARRAY['blocking_reasons','warning_reasons'])
        OR NOT stock_array(m->'validation'->'blocking_reasons','reasons')
        OR NOT stock_array(m->'validation'->'warning_reasons','reasons') THEN RETURN false; END IF;
    FOR v IN SELECT value FROM jsonb_array_elements(m->'offer_revisions') LOOP
        IF NOT stock_keys(v,ARRAY['offer_id','revision']) OR NOT stock_scalar(v->'offer_id','uuid')
            OR NOT stock_scalar(v->'revision','positive') THEN RETURN false; END IF;
        IF previous IS NOT NULL AND v->>'offer_id'<=previous COLLATE "C" THEN RETURN false; END IF;
        previous := v->>'offer_id';
    END LOOP;
    IF m->>'kind'='baseline' AND (p.state<>'ready' OR m->'watermark_seq'<>'null'::jsonb
        OR m->'baseline_publication_id'<>'null'::jsonb OR m->'offer_revisions'<>'[]'::jsonb) THEN RETURN false; END IF;
    IF m->>'kind' IN ('cutover','stock') AND (m->'watermark_seq'='null'::jsonb OR m->'baseline_publication_id'='null'::jsonb) THEN RETURN false; END IF;
    IF jsonb_typeof(p.rows) IS DISTINCT FROM 'array' OR jsonb_array_length(p.rows)<>p.row_count+1 THEN RETURN false; END IF;
    FOR v IN SELECT value FROM jsonb_array_elements(p.rows) LOOP
        IF jsonb_typeof(v) IS DISTINCT FROM 'array' OR jsonb_array_length(v)<>12 THEN RETURN false; END IF;
        FOR cells IN SELECT value FROM jsonb_array_elements(v) LOOP
            IF NOT stock_scalar(cells,'string') THEN RETURN false; END IF;
        END LOOP;
    END LOOP;
    IF NOT stock_keys(p.target_results,ARRAY(SELECT jsonb_object_keys(m->'target_snapshots'))) THEN RETURN false; END IF;
    FOR k,v IN SELECT key,value FROM jsonb_each(m->'target_snapshots') LOOP
        count_targets := count_targets+1;
        IF NOT stock_target(v) OR v->>'id'<>k THEN RETURN false; END IF;
        IF p.ready_at IS NOT NULL THEN
            IF v->'is_active'<>'true'::jsonb THEN RETURN false; END IF;
            FOREACH field_name IN ARRAY ARRAY['name','spreadsheet_id','sheet_name','sa_key_secret_name'] LOOP
                IF v->>field_name='' THEN RETURN false; END IF;
            END LOOP;
        END IF;
        r := p.target_results->k;
        IF NOT stock_keys(r,ARRAY['target_snapshot','status','attempts','verified_rows','verified_sha256','verified_at','review_reason','reservation_attempt_id'])
            OR r->'target_snapshot'<>v OR NOT coalesce(r->>'status' IN ('pending','in_flight','unknown','succeeded','failed'),false)
            OR jsonb_typeof(r->'attempts') IS DISTINCT FROM 'array'
            OR NOT stock_scalar(r->'verified_rows','integer',true) OR NOT stock_scalar(r->'verified_sha256','digest',true)
            OR NOT stock_scalar(r->'verified_at','timestamp',true) OR NOT stock_scalar(r->'reservation_attempt_id','uuid',true)
            OR NOT (r->'review_reason'='null'::jsonb OR coalesce(r->>'review_reason' IN ('target_config_changed','readback_mismatch','outcome_unknown'),false)) THEN RETURN false; END IF;
        keys_seen := '[]'; last_a := NULL;
        FOR a IN SELECT value FROM jsonb_array_elements(r->'attempts') LOOP
            IF NOT stock_keys(a,ARRAY['attempt_id','request_key','request_hash','actor','reason','started_at','finished_at','outcome','error'])
                OR NOT stock_scalar(a->'attempt_id','uuid') OR NOT stock_scalar(a->'request_hash','digest')
                OR NOT stock_scalar(a->'started_at','timestamp') OR NOT stock_scalar(a->'finished_at','timestamp',true)
                OR NOT coalesce(a->>'outcome' IN ('in_flight','unknown','succeeded','failed'),false) THEN RETURN false; END IF;
            FOREACH field_name IN ARRAY ARRAY['request_key','actor','reason'] LOOP
                IF NOT stock_scalar(a->field_name,'nonempty') THEN RETURN false; END IF;
            END LOOP;
            IF a->'error'<>'null'::jsonb AND (jsonb_typeof(a->'error')<>'string' OR a->>'error' !~ '^[a-z0-9_]{1,128}$') THEN RETURN false; END IF;
            IF ids @> jsonb_build_array(a->'attempt_id') OR keys_seen @> jsonb_build_array(a->'request_key') THEN RETURN false; END IF;
            ids := ids || jsonb_build_array(a->'attempt_id'); keys_seen := keys_seen || jsonb_build_array(a->'request_key');
            IF requests ? (a->>'request_key') AND requests->(a->>'request_key')<>jsonb_build_array(a->'request_hash',a->'actor',a->'reason') THEN RETURN false; END IF;
            requests := requests || jsonb_build_object(a->>'request_key',jsonb_build_array(a->'request_hash',a->'actor',a->'reason'));
            IF a->>'outcome'='in_flight' AND (a->'finished_at'<>'null'::jsonb OR a->'error'<>'null'::jsonb) THEN RETURN false; END IF;
            IF a->>'outcome'='unknown' AND (a->'finished_at'<>'null'::jsonb OR a->'error'='null'::jsonb) THEN RETURN false; END IF;
            IF a->>'outcome' IN ('succeeded','failed') THEN
                IF a->'finished_at'='null'::jsonb OR (a->>'finished_at')::timestamptz<(a->>'started_at')::timestamptz THEN RETURN false; END IF;
                IF (a->>'outcome'='succeeded')<>(a->'error'='null'::jsonb) THEN RETURN false; END IF;
            END IF;
            IF last_a IS NOT NULL AND last_a->>'outcome'<>'failed' THEN RETURN false; END IF;
            last_a := a;
        END LOOP;
        IF r->>'status'='pending' THEN
            IF last_a IS NOT NULL OR r->'reservation_attempt_id'<>'null'::jsonb THEN RETURN false; END IF;
        ELSE
            IF last_a IS NULL OR last_a->>'outcome'<>r->>'status' THEN RETURN false; END IF;
        END IF;
        IF r->>'status' IN ('in_flight','unknown') AND r->'reservation_attempt_id' IS DISTINCT FROM last_a->'attempt_id' THEN RETURN false; END IF;
        IF r->'reservation_attempt_id'<>'null'::jsonb THEN
            count_reserved := count_reserved+1;
            IF r->'reservation_attempt_id' IS DISTINCT FROM last_a->'attempt_id' THEN RETURN false; END IF;
        END IF;
        IF r->>'status'='succeeded' THEN
            count_success := count_success+1;
            IF r->'verified_rows' IS DISTINCT FROM to_jsonb(p.row_count) OR r->>'verified_sha256' IS DISTINCT FROM p.rows_sha256
                OR r->'verified_at' IS DISTINCT FROM last_a->'finished_at' THEN RETURN false; END IF;
        ELSIF r->'verified_rows'<>'null'::jsonb OR r->'verified_sha256'<>'null'::jsonb OR r->'verified_at'<>'null'::jsonb THEN RETURN false;
        END IF;
        IF r->>'status'='failed' THEN count_failed := count_failed+1; END IF;
        IF r->>'status'='unknown' AND NOT coalesce(r->>'review_reason' IN ('outcome_unknown','target_config_changed'),false) THEN RETURN false; END IF;
        IF last_a->>'error'='readback_mismatch' AND NOT coalesce(r->>'review_reason' IN ('readback_mismatch','target_config_changed'),false) THEN RETURN false; END IF;
        IF p.state IN ('building','ready') AND r->>'status'<>'pending' THEN RETURN false; END IF;
        IF p.state='failed' AND p.ready_at IS NULL AND last_a IS NOT NULL THEN RETURN false; END IF;
    END LOOP;
    IF p.ready_at IS NOT NULL AND count_targets=0 THEN RETURN false; END IF;
    IF p.state='completed' AND (count_success<>count_targets OR count_reserved<>0) THEN RETURN false; END IF;
    IF p.state='partial' AND NOT (count_success>0 AND count_success<count_targets) THEN RETURN false; END IF;
    IF p.state='failed' AND p.ready_at IS NOT NULL AND count_failed<>count_targets THEN RETURN false; END IF;
    IF p.state='delivering' AND count_success=count_targets THEN RETURN false; END IF;
    RETURN true;
END $fn$;
CREATE OR REPLACE FUNCTION stock_audit_shape(v jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE o jsonb; e jsonb; k text; previous text;
BEGIN
    IF NOT stock_keys(v,ARRAY['offer','plans','validated_inputs']) OR jsonb_typeof(v->'plans') IS DISTINCT FROM 'array'
        OR jsonb_typeof(v->'validated_inputs') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
    o := v->'offer';
    IF o='null'::jsonb THEN RETURN v->'plans'='[]'::jsonb AND v->'validated_inputs'='[]'::jsonb; END IF;
    IF NOT stock_keys(o,ARRAY['id','revision','supplier_channel_id','product_id','unit_id','condition_id','shipping_label','shipping_evidence','quantity','price','availability','quantity_event_id','price_event_id','condition_event_id','validation_event_id'])
        OR NOT stock_scalar(o->'revision','positive') OR NOT stock_scalar(o->'shipping_label','string',true)
        OR jsonb_typeof(o->'shipping_evidence') IS DISTINCT FROM 'array'
        OR NOT stock_scalar(o->'quantity','decimal',true) OR NOT stock_scalar(o->'price','decimal',true)
        OR NOT coalesce(o->>'availability' IN ('available','sold_out','unknown'),false) THEN RETURN false; END IF;
    IF (o->>'availability'='unknown' AND o->'quantity'<>'null'::jsonb)
        OR (o->>'availability'='available' AND (o->'quantity'='null'::jsonb OR (o->>'quantity')::numeric<=0))
        OR (o->>'availability'='sold_out' AND (o->'quantity'='null'::jsonb OR (o->>'quantity')::numeric<>0)) THEN RETURN false; END IF;
    FOREACH k IN ARRAY ARRAY['id','supplier_channel_id','product_id','unit_id','condition_id'] LOOP
        IF NOT stock_scalar(o->k,'uuid') THEN RETURN false; END IF;
    END LOOP;
    FOREACH k IN ARRAY ARRAY['quantity_event_id','price_event_id','condition_event_id','validation_event_id'] LOOP
        IF NOT stock_scalar(o->k,'uuid',true) THEN RETURN false; END IF;
    END LOOP;
    FOR e IN SELECT value FROM jsonb_array_elements(v->'plans') LOOP
        IF NOT stock_keys(e,ARRAY['id','revision','polarity','certainty_raw','date_kind','date_precision','date_raw','date_start','date_end','resolution','review_reason','source_event_id'])
            OR NOT stock_scalar(e->'id','uuid') OR NOT stock_scalar(e->'source_event_id','uuid') OR NOT stock_scalar(e->'revision','positive') THEN RETURN false; END IF;
        IF previous IS NOT NULL AND e->>'id'<=previous COLLATE "C" THEN RETURN false; END IF;
        previous := e->>'id';
        FOREACH k IN ARRAY ARRAY['certainty_raw','date_raw'] LOOP
            IF NOT stock_scalar(e->k,'string') THEN RETURN false; END IF;
        END LOOP;
        IF NOT coalesce(e->>'polarity' IN ('positive','negative','unknown'),false)
            OR NOT coalesce(e->>'date_kind' IN ('arrival','shipment','order_cutoff','unknown'),false)
            OR NOT coalesce(e->>'date_precision' IN ('day','range','period','unspecified'),false)
            OR NOT coalesce(e->>'resolution' IN ('resolved','unspecified','needs_review'),false)
            OR NOT stock_scalar(e->'date_start','date',true) OR NOT stock_scalar(e->'date_end','date',true)
            OR NOT stock_scalar(e->'review_reason','nonempty',true) THEN RETURN false; END IF;
        IF e->>'date_precision'='period' AND e->>'date_raw'='' THEN RETURN false; END IF;
        IF e->>'resolution'='resolved' THEN
            IF e->'date_start'='null'::jsonb OR e->'date_end'='null'::jsonb OR e->'review_reason'<>'null'::jsonb
                OR e->>'date_precision' NOT IN ('day','range') OR e->>'date_start'>e->>'date_end'
                OR (e->>'date_precision'='day' AND e->'date_start'<>e->'date_end') THEN RETURN false; END IF;
        ELSE
            IF e->'date_start'<>'null'::jsonb OR e->'date_end'<>'null'::jsonb THEN RETURN false; END IF;
            IF e->>'resolution'='unspecified' AND (e->'review_reason'<>'null'::jsonb OR e->>'date_precision' NOT IN ('period','unspecified')) THEN RETURN false; END IF;
            IF e->>'resolution'='needs_review' AND e->'review_reason'='null'::jsonb THEN RETURN false; END IF;
        END IF;
    END LOOP;
    previous := NULL;
    FOR e IN SELECT value FROM jsonb_array_elements(v->'validated_inputs') LOOP
        IF NOT stock_keys(e,ARRAY['field_key','event_id','proposal_input_digest']) OR NOT stock_scalar(e->'field_key','nonempty')
            OR NOT stock_scalar(e->'event_id','uuid') OR NOT stock_scalar(e->'proposal_input_digest','digest') THEN RETURN false; END IF;
        k := e->>'field_key';
        IF k NOT IN ('identity','quantity','price','condition') AND NOT (left(k,5)='plan:' AND stock_scalar(to_jsonb(substring(k FROM 6)),'uuid')) THEN RETURN false; END IF;
        IF previous IS NOT NULL AND k<=previous COLLATE "C" THEN RETURN false; END IF;
        previous := k;
    END LOOP;
    RETURN true;
END $fn$;
$ddl$;
        EXECUTE $ddl$
CREATE OR REPLACE FUNCTION stock_check_event(eid uuid) RETURNS void
LANGUAGE plpgsql SET search_path FROM CURRENT AS $fn$
DECLARE e tcg_stock_events; o tcg_stock_offers; src source_messages; ref tcg_stock_events; v jsonb; snap jsonb;
    linked_source uuid;
BEGIN
    SELECT * INTO e FROM tcg_stock_events WHERE id=eid;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT * INTO src FROM source_messages WHERE id=e.source_message_id FOR SHARE;
    IF NOT FOUND OR e.source_posted_at IS DISTINCT FROM src.line_posted_at
        OR e.analysis_result_snapshot->'proposal'->'target_selector'->>'channel_id' IS DISTINCT FROM src.supplier_channel_id::text
        THEN RAISE EXCEPTION 'stock event source mismatch'; END IF;
    IF e.extraction_item_id IS NOT NULL THEN
        SELECT j.source_message_id INTO linked_source FROM extraction_items i JOIN extraction_jobs j ON j.id=i.extraction_job_id WHERE i.id=e.extraction_item_id FOR SHARE OF i,j;
        IF linked_source IS DISTINCT FROM e.source_message_id THEN RAISE EXCEPTION 'stock extraction source mismatch'; END IF;
    END IF;
    IF (e.analysis_result_snapshot->>'kind'='no_item')<>(e.extraction_item_id IS NULL)
        OR (e.analysis_input_snapshot->'extraction_payload'='null'::jsonb)<>(e.extraction_item_id IS NULL)
        OR (e.extraction_item_id IS NULL AND e.decision='applied') THEN RAISE EXCEPTION 'stock item presence mismatch'; END IF;
    IF e.analysis_result_snapshot->>'extraction_item_id' IS DISTINCT FROM e.extraction_item_id::text THEN RAISE EXCEPTION 'stock snapshot item mismatch'; END IF;
    IF e.offer_id IS NOT NULL THEN
        SELECT * INTO o FROM tcg_stock_offers WHERE id=e.offer_id;
        IF NOT FOUND OR o.supplier_channel_id IS DISTINCT FROM src.supplier_channel_id THEN RAISE EXCEPTION 'stock event offer channel mismatch'; END IF;
    END IF;
    IF e.decision='applied' THEN
        IF e.source_posted_at IS NULL OR e.applied_offer_revision>o.revision
            OR e.after_values->'offer'->>'id' IS DISTINCT FROM e.offer_id::text
            OR (e.after_values->'offer'->>'revision')::bigint IS DISTINCT FROM e.applied_offer_revision THEN RAISE EXCEPTION 'stock applied audit mismatch'; END IF;
    ELSE
        IF e.before_values<>'{"offer":null,"plans":[],"validated_inputs":[]}'::jsonb
            OR e.after_values<>'{"offer":null,"plans":[],"validated_inputs":[]}'::jsonb THEN RAISE EXCEPTION 'stock unapplied audit must be empty'; END IF;
    END IF;
    FOREACH snap IN ARRAY ARRAY[e.before_values,e.after_values] LOOP
        IF snap->'offer'<>'null'::jsonb AND (snap->'offer'->>'id' IS DISTINCT FROM e.offer_id::text
            OR snap->'offer'->>'supplier_channel_id' IS DISTINCT FROM src.supplier_channel_id::text) THEN RAISE EXCEPTION 'stock audit other offer'; END IF;
        FOR v IN SELECT value FROM jsonb_array_elements(snap->'validated_inputs') LOOP
            SELECT * INTO ref FROM tcg_stock_events WHERE id=(v->>'event_id')::uuid;
            IF NOT FOUND OR ref.decision<>'applied' OR ref.offer_id IS DISTINCT FROM e.offer_id THEN RAISE EXCEPTION 'stock audit contributor mismatch'; END IF;
            IF v->>'field_key'='identity' AND (ref.before_values->'offer'<>'null'::jsonb OR ref.after_values->'offer'->>'id' IS DISTINCT FROM e.offer_id::text)
                THEN RAISE EXCEPTION 'stock identity contributor mismatch'; END IF;
        END LOOP;
    END LOOP;
END $fn$;
CREATE OR REPLACE FUNCTION stock_check_offer(oid uuid) RETURNS void
LANGUAGE plpgsql SET search_path FROM CURRENT AS $fn$
DECLARE o tcg_stock_offers; e tcg_stock_events; pid uuid; v jsonb; expected jsonb := '{}'; actual jsonb := '{}'; k text; plan_row tcg_restock_plans;
BEGIN
    SELECT * INTO o FROM tcg_stock_offers WHERE id=oid;
    IF NOT FOUND THEN RETURN; END IF;
    FOREACH pid IN ARRAY ARRAY[o.quantity_event_id,o.price_event_id,o.condition_event_id,o.validation_event_id] LOOP
        IF pid IS NOT NULL THEN
            SELECT * INTO e FROM tcg_stock_events WHERE id=pid;
            IF NOT FOUND OR e.offer_id IS DISTINCT FROM oid OR e.decision<>'applied' THEN RAISE EXCEPTION 'stock offer contributor mismatch'; END IF;
            PERFORM stock_check_event(pid);
        END IF;
    END LOOP;
    FOR plan_row IN SELECT * FROM tcg_restock_plans WHERE offer_id=oid LOOP
        SELECT * INTO e FROM tcg_stock_events WHERE id=plan_row.source_event_id;
        IF NOT FOUND OR e.offer_id IS DISTINCT FROM oid OR e.decision<>'applied' THEN RAISE EXCEPTION 'stock plan contributor mismatch'; END IF;
        expected := expected || jsonb_build_object('plan:'||plan_row.id,plan_row.source_event_id::text);
    END LOOP;
    IF o.validation_event_id IS NULL THEN RETURN; END IF;
    SELECT * INTO e FROM tcg_stock_events WHERE id=o.validation_event_id;
    IF e.applied_offer_revision<>o.revision THEN RAISE EXCEPTION 'stock validation revision mismatch'; END IF;
    IF o.quantity_event_id IS NOT NULL THEN expected:=expected||jsonb_build_object('quantity',o.quantity_event_id::text); END IF;
    IF o.price_event_id IS NOT NULL THEN expected:=expected||jsonb_build_object('price',o.price_event_id::text); END IF;
    IF o.condition_event_id IS NOT NULL THEN expected:=expected||jsonb_build_object('condition',o.condition_event_id::text); END IF;
    FOR v IN SELECT value FROM jsonb_array_elements(e.after_values->'validated_inputs') LOOP
        actual := actual || jsonb_build_object(v->>'field_key',v->>'event_id');
    END LOOP;
    IF NOT actual ? 'identity' OR actual-'identity'<>expected THEN RAISE EXCEPTION 'stock validation contributors incomplete'; END IF;
    FOREACH k IN ARRAY ARRAY['supplier_channel_id','product_id','unit_id','condition_id','shipping_label','availability','quantity_event_id','price_event_id','condition_event_id','validation_event_id'] LOOP
        IF e.after_values->'offer'->k IS DISTINCT FROM to_jsonb(o)->k THEN RAISE EXCEPTION 'stock validation offer mismatch'; END IF;
    END LOOP;
    IF (e.after_values->'offer'->>'quantity')::numeric IS DISTINCT FROM o.quantity
        OR (e.after_values->'offer'->>'price')::numeric IS DISTINCT FROM o.price
        OR e.after_values->'offer'->'shipping_evidence' IS DISTINCT FROM o.shipping_evidence THEN RAISE EXCEPTION 'stock validation values mismatch'; END IF;
    FOR plan_row IN SELECT * FROM tcg_restock_plans WHERE offer_id=oid LOOP
        SELECT value INTO v FROM jsonb_array_elements(e.after_values->'plans') WHERE value->>'id'=plan_row.id::text;
        IF v IS DISTINCT FROM to_jsonb(plan_row)-ARRAY['offer_id','created_at','updated_at'] THEN RAISE EXCEPTION 'stock validation plan contents mismatch'; END IF;
    END LOOP;
    IF ARRAY(SELECT value->>'id' FROM jsonb_array_elements(e.after_values->'plans'))
        IS DISTINCT FROM ARRAY(SELECT id::text FROM tcg_restock_plans WHERE offer_id=oid ORDER BY id) THEN RAISE EXCEPTION 'stock validation plan set mismatch'; END IF;
END $fn$;
CREATE OR REPLACE FUNCTION stock_check_publication(pid uuid, entering_ready boolean DEFAULT false) RETURNS void
LANGUAGE plpgsql SET search_path FROM CURRENT AS $fn$
DECLARE p tcg_stock_publications; c tcg_stock_control; b tcg_stock_publications; t tcg_distribution_targets;
    k text; v jsonb; r jsonb; expected_id uuid;
BEGIN
    SELECT * INTO p FROM tcg_stock_publications WHERE id=pid;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT * INTO c FROM tcg_stock_control WHERE id=1;
    IF p.input_manifest->>'rollout_id' IS DISTINCT FROM c.rollout_id::text THEN RAISE EXCEPTION 'stock publication rollout mismatch'; END IF;
    FOR v IN SELECT value FROM jsonb_array_elements(p.input_manifest->'source_ids') LOOP
        IF NOT EXISTS(SELECT 1 FROM source_messages WHERE id=(v #>> '{}')::uuid) THEN RAISE EXCEPTION 'stock publication source missing'; END IF;
    END LOOP;
    FOR v IN SELECT value FROM jsonb_array_elements(p.input_manifest->'offer_revisions') LOOP
        IF NOT EXISTS(SELECT 1 FROM tcg_stock_offers WHERE id=(v->>'offer_id')::uuid) THEN RAISE EXCEPTION 'stock publication offer missing'; END IF;
    END LOOP;
    IF p.input_manifest->'baseline_publication_id'<>'null'::jsonb THEN
        SELECT * INTO b FROM tcg_stock_publications WHERE id=(p.input_manifest->>'baseline_publication_id')::uuid;
        IF NOT FOUND OR b.state<>'ready' OR b.input_manifest->>'kind'<>'baseline'
            OR b.input_manifest->'rollout_id'<>p.input_manifest->'rollout_id' THEN RAISE EXCEPTION 'stock publication baseline mismatch'; END IF;
    END IF;
    IF entering_ready AND p.input_manifest->>'kind'='cutover'
        AND NOT(c.mode='paused' AND c.resume_mode='shadow' AND c.watermark_seq=(p.input_manifest->>'watermark_seq')::bigint)
        THEN RAISE EXCEPTION 'stock cutover requires paused shadow'; END IF;
    FOR k,v IN SELECT key,value FROM jsonb_each(p.input_manifest->'target_snapshots') LOOP
        SELECT * INTO t FROM tcg_distribution_targets WHERE id=k::uuid;
        IF NOT FOUND THEN RAISE EXCEPTION 'stock publication target missing'; END IF;
        IF entering_ready AND stock_target_value(t)<>v THEN RAISE EXCEPTION 'stock ready target mismatch'; END IF;
        r := p.target_results->k;
        expected_id := CASE WHEN r->'reservation_attempt_id'<>'null'::jsonb THEN pid ELSE NULL END;
        IF expected_id IS NOT NULL AND t.active_publication_id IS DISTINCT FROM pid THEN RAISE EXCEPTION 'stock result reservation missing'; END IF;
        IF expected_id IS NULL AND t.active_publication_id=pid THEN RAISE EXCEPTION 'stock target reservation not released'; END IF;
    END LOOP;
END $fn$;
CREATE OR REPLACE FUNCTION stock_resolution_shape(v jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path FROM CURRENT AS $fn$
DECLARE r jsonb; k jsonb;
BEGIN
    IF NOT stock_keys(v,ARRAY['event_id','decision','offer_id','applied_offer_revision','reason','reconciliation'])
        OR NOT stock_scalar(v->'event_id','uuid') OR NOT stock_scalar(v->'offer_id','uuid',true)
        OR NOT stock_scalar(v->'applied_offer_revision','positive',true) OR NOT stock_scalar(v->'reason','nonempty')
        OR NOT coalesce(v->>'decision' IN ('pending','applied','ignored','stale','rejected'),false) THEN RETURN false; END IF;
    r := v->'reconciliation';
    IF r='null'::jsonb THEN RETURN true; END IF;
    IF NOT stock_keys(r,ARRAY['action','previous_event_id','field_keys','observed_result_digest','confirmed_values','effect_event_id'])
        OR NOT coalesce(r->>'action' IN ('confirm_previous','accept_revision'),false)
        OR NOT stock_scalar(r->'previous_event_id','uuid') OR NOT stock_scalar(r->'effect_event_id','uuid')
        OR NOT stock_scalar(r->'observed_result_digest','digest') OR NOT stock_array(r->'field_keys','reasons')
        OR jsonb_typeof(r->'confirmed_values') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
    FOR k IN SELECT value FROM jsonb_array_elements(r->'field_keys') LOOP
        IF k #>> '{}' NOT IN ('identity','quantity','price','condition') AND NOT
            (left(k #>> '{}',5)='plan:' AND stock_scalar(to_jsonb(substring(k #>> '{}' FROM 6)),'uuid')) THEN RETURN false; END IF;
    END LOOP;
    RETURN true;
END $fn$;
CREATE OR REPLACE FUNCTION stock_row_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path FROM CURRENT AS $fn$
DECLARE k text; a jsonb; prior jsonb; r jsonb; old_r jsonb; i integer; p tcg_stock_publications;
BEGIN
    IF TG_OP='DELETE' THEN
        IF TG_TABLE_NAME='tcg_distribution_targets' THEN
            IF OLD.active_publication_id IS NOT NULL OR EXISTS(SELECT 1 FROM tcg_stock_publications WHERE input_manifest->'target_snapshots' ? OLD.id::text)
                THEN RAISE EXCEPTION 'stock referenced target cannot be removed'; END IF;
            RETURN OLD;
        END IF;
        RAISE EXCEPTION 'stock history cannot be removed';
    END IF;
    IF TG_TABLE_NAME='tcg_stock_events' THEN
        IF NEW.resolution_response IS NOT NULL AND (NOT stock_resolution_shape(NEW.resolution_response)
            OR NEW.resolution_response->>'event_id' IS DISTINCT FROM NEW.id::text
            OR NEW.resolution_response->>'decision' IS DISTINCT FROM NEW.decision
            OR NEW.resolution_response->>'offer_id' IS DISTINCT FROM NEW.offer_id::text
            OR (NEW.resolution_response->>'applied_offer_revision')::bigint IS DISTINCT FROM NEW.applied_offer_revision)
            THEN RAISE EXCEPTION 'stock resolution response mismatch'; END IF;
        IF NOT stock_audit_shape(NEW.before_values) OR NOT stock_audit_shape(NEW.after_values) THEN RAISE EXCEPTION 'stock audit shape invalid'; END IF;
        IF TG_OP='UPDATE' THEN
            IF OLD.decision<>'pending' AND NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'stock terminal event immutable'; END IF;
            IF (to_jsonb(NEW)-ARRAY['offer_id','review_reasons','resolution_key','resolution_request_hash','resolved_by','resolved_at','resolution_response','decision','before_values','after_values','applied_offer_revision','applied_at'])
                IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['offer_id','review_reasons','resolution_key','resolution_request_hash','resolved_by','resolved_at','resolution_response','decision','before_values','after_values','applied_offer_revision','applied_at']) THEN RAISE EXCEPTION 'stock event inputs immutable'; END IF;
        END IF;
    ELSIF TG_TABLE_NAME='tcg_stock_offers' THEN
        IF TG_OP='UPDATE' AND NEW IS DISTINCT FROM OLD THEN
            IF ROW(NEW.id,NEW.supplier_channel_id,NEW.product_id,NEW.unit_id,NEW.shipping_label,NEW.shipping_evidence,NEW.created_at)
                IS DISTINCT FROM ROW(OLD.id,OLD.supplier_channel_id,OLD.product_id,OLD.unit_id,OLD.shipping_label,OLD.shipping_evidence,OLD.created_at)
                OR NEW.revision<>OLD.revision+1 THEN RAISE EXCEPTION 'stock offer identity or revision invalid'; END IF;
        END IF;
    ELSIF TG_TABLE_NAME='tcg_restock_plans' THEN
        IF TG_OP='UPDATE' AND NEW IS DISTINCT FROM OLD AND (ROW(NEW.id,NEW.offer_id,NEW.created_at) IS DISTINCT FROM ROW(OLD.id,OLD.offer_id,OLD.created_at)
            OR NEW.revision<>OLD.revision+1) THEN RAISE EXCEPTION 'stock plan identity or revision invalid'; END IF;
    ELSIF TG_TABLE_NAME='tcg_stock_inbox' THEN
        IF TG_OP='UPDATE' THEN
            IF ROW(NEW.source_message_id,NEW.seq,NEW.created_at) IS DISTINCT FROM ROW(OLD.source_message_id,OLD.seq,OLD.created_at)
                OR NEW.attempt_count<OLD.attempt_count THEN RAISE EXCEPTION 'stock inbox identity immutable'; END IF;
            IF OLD.state='settled' AND NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'stock settled inbox immutable'; END IF;
            IF OLD.state='error' AND NEW.state NOT IN ('error','pending') THEN RAISE EXCEPTION 'stock inbox retry must be pending'; END IF;
            IF OLD.error_code IS NOT NULL AND NEW.error_code IS NULL THEN RAISE EXCEPTION 'stock inbox error history required'; END IF;
        END IF;
    ELSIF TG_TABLE_NAME='tcg_stock_control' THEN
        IF TG_OP='UPDATE' AND NEW IS DISTINCT FROM OLD THEN
            IF NEW.rollout_id<>OLD.rollout_id OR NEW.id<>OLD.id OR NEW.revision<>OLD.revision+1 OR NEW.next_seq<OLD.next_seq
                THEN RAISE EXCEPTION 'stock control identity or revision invalid'; END IF;
            IF NEW.mode<>OLD.mode AND NOT (
                (OLD.mode='legacy' AND NEW.mode='shadow')
                OR (OLD.mode IN ('legacy','shadow','projected') AND NEW.mode='paused' AND NEW.resume_mode=OLD.mode)
                OR (OLD.mode='paused' AND NEW.mode=OLD.resume_mode)
                OR (OLD.mode='paused' AND OLD.resume_mode='shadow' AND NEW.mode='projected' AND NEW.approved_publication_id IS NOT NULL))
                THEN RAISE EXCEPTION 'stock control transition invalid'; END IF;
        END IF;
    ELSIF TG_TABLE_NAME='tcg_stock_publications' THEN
        IF NOT stock_publication_shape(NEW) THEN RAISE EXCEPTION 'stock publication shape invalid'; END IF;
        IF TG_OP='UPDATE' THEN
            IF OLD.state='completed' AND NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'stock completed publication immutable'; END IF;
            IF NEW.id<>OLD.id OR NEW.created_at<>OLD.created_at THEN RAISE EXCEPTION 'stock publication identity immutable'; END IF;
            IF OLD.ready_at IS NOT NULL AND ROW(NEW.rows,NEW.rows_sha256,NEW.row_count,NEW.input_manifest,NEW.schema_version,NEW.ready_at)
                IS DISTINCT FROM ROW(OLD.rows,OLD.rows_sha256,OLD.row_count,OLD.input_manifest,OLD.schema_version,OLD.ready_at) THEN RAISE EXCEPTION 'stock ready payload immutable'; END IF;
            IF NEW.state<>OLD.state AND NOT (
                (OLD.state='building' AND NEW.state IN ('ready','failed')) OR (OLD.state='ready' AND NEW.state='delivering')
                OR (OLD.state='delivering' AND NEW.state IN ('completed','partial','failed'))
                OR (OLD.state IN ('partial','failed') AND OLD.ready_at IS NOT NULL AND NEW.state='delivering'))
                THEN RAISE EXCEPTION 'stock publication transition invalid'; END IF;
            FOR k,r IN SELECT key,value FROM jsonb_each(NEW.target_results) LOOP
                old_r := OLD.target_results->k;
                IF old_r IS NULL THEN CONTINUE; END IF;
                IF jsonb_array_length(r->'attempts')<jsonb_array_length(old_r->'attempts') THEN RAISE EXCEPTION 'stock attempts cannot be removed'; END IF;
                FOR i IN 0..jsonb_array_length(old_r->'attempts')-1 LOOP
                    a := r->'attempts'->i; prior := old_r->'attempts'->i;
                    IF a-ARRAY['finished_at','outcome','error'] IS DISTINCT FROM prior-ARRAY['finished_at','outcome','error']
                        THEN RAISE EXCEPTION 'stock attempt request immutable'; END IF;
                    IF prior->>'outcome' IN ('succeeded','failed') AND a<>prior THEN RAISE EXCEPTION 'stock terminal attempt immutable'; END IF;
                    IF prior->>'outcome'='unknown' AND a->>'outcome' NOT IN ('unknown','succeeded','failed') THEN RAISE EXCEPTION 'stock unknown attempt unresolved'; END IF;
                END LOOP;
                IF jsonb_array_length(r->'attempts')>jsonb_array_length(old_r->'attempts') THEN
                    IF jsonb_array_length(r->'attempts')<>jsonb_array_length(old_r->'attempts')+1
                        OR old_r->>'status' NOT IN ('pending','failed') OR old_r->'reservation_attempt_id'<>'null'::jsonb
                        OR r->'review_reason'<>'null'::jsonb THEN RAISE EXCEPTION 'stock retry not permitted'; END IF;
                END IF;
                IF old_r->>'status'='succeeded' AND r-ARRAY['reservation_attempt_id','review_reason']<>old_r-ARRAY['reservation_attempt_id','review_reason']
                    THEN RAISE EXCEPTION 'stock success result immutable'; END IF;
            END LOOP;
        END IF;
    END IF;
    RETURN NEW;
END $fn$;
$ddl$;
        EXECUTE $ddl$
CREATE OR REPLACE FUNCTION stock_target_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path FROM CURRENT AS $fn$
BEGIN
    IF TG_OP='DELETE' THEN
        IF OLD.active_publication_id IS NOT NULL OR EXISTS(SELECT 1 FROM tcg_stock_publications WHERE input_manifest->'target_snapshots' ? OLD.id::text)
            THEN RAISE EXCEPTION 'stock referenced target cannot be removed'; END IF;
        RETURN OLD;
    END IF;
    IF OLD.active_publication_id IS NOT NULL AND NEW.active_publication_id IS NOT NULL AND NEW.active_publication_id<>OLD.active_publication_id
        THEN RAISE EXCEPTION 'stock reservation cannot be transferred'; END IF;
    IF OLD.id<>NEW.id AND EXISTS(SELECT 1 FROM tcg_stock_publications WHERE input_manifest->'target_snapshots' ? OLD.id::text)
        THEN RAISE EXCEPTION 'stock referenced target identity immutable'; END IF;
    IF OLD.active_publication_id IS NOT NULL AND stock_target_value(NEW)<>stock_target_value(OLD) THEN
        UPDATE tcg_stock_publications SET target_results=jsonb_set(target_results,
            ARRAY[OLD.id::text,'review_reason'],'"target_config_changed"'::jsonb)
            WHERE id=OLD.active_publication_id;
    END IF;
    RETURN NEW;
END $fn$;
CREATE OR REPLACE FUNCTION stock_source_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path FROM CURRENT AS $fn$
BEGIN
    IF EXISTS(SELECT 1 FROM tcg_stock_publications WHERE input_manifest->'source_ids' @> jsonb_build_array(OLD.id::text))
        THEN RAISE EXCEPTION 'stock published source cannot be removed'; END IF;
    RETURN OLD;
END $fn$;
CREATE OR REPLACE FUNCTION stock_deferred_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path FROM CURRENT AS $fn$
DECLARE eid uuid; oid uuid; p tcg_stock_publications; c tcg_stock_control; r jsonb; v jsonb; t tcg_distribution_targets;
BEGIN
    IF TG_TABLE_NAME='tcg_stock_events' THEN
        PERFORM stock_check_event(NEW.id);
        IF NEW.offer_id IS NOT NULL THEN PERFORM stock_check_offer(NEW.offer_id); END IF;
    ELSIF TG_TABLE_NAME='tcg_stock_offers' THEN
        PERFORM stock_check_offer(NEW.id);
    ELSIF TG_TABLE_NAME='tcg_restock_plans' THEN
        PERFORM stock_check_offer(NEW.offer_id);
    ELSIF TG_TABLE_NAME IN ('source_messages','extraction_items','extraction_jobs') THEN
        IF TG_TABLE_NAME='source_messages' THEN
            FOR eid IN SELECT id FROM tcg_stock_events WHERE source_message_id=NEW.id LOOP PERFORM stock_check_event(eid); END LOOP;
        ELSIF TG_TABLE_NAME='extraction_items' THEN
            FOR eid IN SELECT id FROM tcg_stock_events WHERE extraction_item_id=NEW.id LOOP PERFORM stock_check_event(eid); END LOOP;
        ELSE
            FOR eid IN SELECT e.id FROM tcg_stock_events e JOIN extraction_items i ON i.id=e.extraction_item_id WHERE i.extraction_job_id=NEW.id LOOP PERFORM stock_check_event(eid); END LOOP;
        END IF;
    ELSIF TG_TABLE_NAME='tcg_stock_inbox' THEN
        SELECT event_ids INTO r FROM tcg_stock_inbox WHERE source_message_id=NEW.source_message_id;
        FOR v IN SELECT value FROM jsonb_array_elements(r) LOOP
            IF NOT EXISTS(SELECT 1 FROM tcg_stock_events WHERE id=(v #>> '{}')::uuid AND source_message_id=NEW.source_message_id)
                THEN RAISE EXCEPTION 'stock inbox event source mismatch'; END IF;
        END LOOP;
    ELSIF TG_TABLE_NAME='tcg_stock_control' THEN
        SELECT * INTO c FROM tcg_stock_control WHERE id=1;
        IF c.baseline_publication_id IS NOT NULL THEN
            SELECT * INTO p FROM tcg_stock_publications WHERE id=c.baseline_publication_id;
            IF NOT FOUND OR p.state<>'ready' OR p.input_manifest->>'kind'<>'baseline' OR p.input_manifest->>'rollout_id'<>c.rollout_id::text
                THEN RAISE EXCEPTION 'stock control baseline mismatch'; END IF;
        END IF;
        IF c.approved_publication_id IS NOT NULL THEN
            SELECT * INTO p FROM tcg_stock_publications WHERE id=c.approved_publication_id;
            IF NOT FOUND OR p.ready_at IS NULL OR p.input_manifest->>'kind'<>'cutover' OR p.input_manifest->>'rollout_id'<>c.rollout_id::text
                THEN RAISE EXCEPTION 'stock control approval mismatch'; END IF;
        END IF;
    ELSIF TG_TABLE_NAME='tcg_stock_publications' THEN
        PERFORM stock_check_publication(NEW.id,NEW.ready_at IS NOT NULL AND (TG_OP='INSERT' OR OLD.ready_at IS NULL));
        IF TG_OP='UPDATE' THEN
            FOR v IN SELECT to_jsonb(key) FROM jsonb_each(OLD.target_results) LOOP
                r := NEW.target_results->(v #>> '{}');
                IF OLD.target_results->(v #>> '{}')->'reservation_attempt_id'<>'null'::jsonb AND r->'reservation_attempt_id'='null'::jsonb THEN
                    IF r->>'status' NOT IN ('succeeded','failed') OR OLD.target_results->(v #>> '{}')->'reservation_attempt_id'
                        IS DISTINCT FROM r->'attempts'->-1->'attempt_id' THEN RAISE EXCEPTION 'stock unresolved reservation release'; END IF;
                END IF;
            END LOOP;
        END IF;
    ELSIF TG_TABLE_NAME='tcg_distribution_targets' THEN
        SELECT * INTO t FROM tcg_distribution_targets WHERE id=NEW.id;
        IF OLD.active_publication_id IS NULL AND NEW.active_publication_id IS NOT NULL THEN
            SELECT * INTO p FROM tcg_stock_publications WHERE id=NEW.active_publication_id;
            SELECT * INTO c FROM tcg_stock_control WHERE id=1;
            r := p.target_results->NEW.id::text;
            IF NOT FOUND OR p.state<>'delivering' OR r->>'status' IS DISTINCT FROM 'in_flight'
                OR r->'review_reason'<>'null'::jsonb OR r->'reservation_attempt_id' IS DISTINCT FROM r->'attempts'->-1->'attempt_id'
                OR r->'target_snapshot' IS DISTINCT FROM stock_target_value(t) OR NOT t.is_active
                OR t.active_publication_id IS DISTINCT FROM p.id THEN RAISE EXCEPTION 'stock reservation target mismatch'; END IF;
            IF NOT ((p.input_manifest->>'kind'='legacy_stock' AND c.mode IN ('legacy','shadow'))
                OR (p.input_manifest->>'kind'='stock' AND c.mode='projected')
                OR (p.input_manifest->>'kind'='cutover' AND c.mode='projected' AND c.approved_publication_id=p.id))
                THEN RAISE EXCEPTION 'stock reservation mode disallows publication'; END IF;
            PERFORM stock_check_publication(p.id);
        ELSIF OLD.active_publication_id IS NOT NULL AND NEW.active_publication_id IS NULL THEN
            SELECT * INTO p FROM tcg_stock_publications WHERE id=OLD.active_publication_id;
            r := p.target_results->NEW.id::text;
            IF r->>'status' NOT IN ('succeeded','failed') OR r->'reservation_attempt_id'<>'null'::jsonb OR t.active_publication_id IS NOT NULL
                THEN RAISE EXCEPTION 'stock reservation outcome unresolved'; END IF;
        END IF;
    END IF;
    RETURN NULL;
END $fn$;
$ddl$;
        FOREACH column_name IN ARRAY ARRAY['quantity_event_id','price_event_id','condition_event_id','validation_event_id'] LOOP
            IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid=to_regclass(format('%I.tcg_stock_offers',ns)) AND conname='stock_fk_'||column_name) THEN
                EXECUTE format('ALTER TABLE %I.tcg_stock_offers ADD CONSTRAINT %I FOREIGN KEY(%I) REFERENCES %I.tcg_stock_events(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED',ns,'stock_fk_'||column_name,column_name,ns);
            END IF;
            EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I.tcg_stock_offers(%I)','stock_ix_'||column_name,ns,column_name);
        END LOOP;
        IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid=to_regclass(format('%I.extraction_items',ns)) AND conname='stock_evidence_payload_check') THEN
            EXECUTE format('ALTER TABLE %I.extraction_items ADD CONSTRAINT stock_evidence_payload_check CHECK(evidence_payload IS NULL OR %I.stock_evidence_shape(evidence_payload))',ns,ns);
        END IF;
        IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid=to_regclass(format('%I.tcg_distribution_targets',ns)) AND conname='stock_active_publication_fk') THEN
            EXECUTE format('ALTER TABLE %I.tcg_distribution_targets ADD CONSTRAINT stock_active_publication_fk FOREIGN KEY(active_publication_id) REFERENCES %I.tcg_stock_publications(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED',ns,ns);
        END IF;
        EXECUTE $ddl$
CREATE INDEX IF NOT EXISTS stock_offer_identity_idx ON tcg_stock_offers(supplier_channel_id,product_id,unit_id,condition_id);
CREATE INDEX IF NOT EXISTS stock_offer_product_idx ON tcg_stock_offers(product_id);
CREATE INDEX IF NOT EXISTS stock_offer_unit_idx ON tcg_stock_offers(unit_id);
CREATE INDEX IF NOT EXISTS stock_offer_condition_idx ON tcg_stock_offers(condition_id);
CREATE INDEX IF NOT EXISTS stock_event_source_idx ON tcg_stock_events(source_message_id,created_at,id);
CREATE INDEX IF NOT EXISTS stock_event_offer_idx ON tcg_stock_events(offer_id,created_at,id);
CREATE INDEX IF NOT EXISTS stock_event_decision_idx ON tcg_stock_events(decision,created_at,id);
CREATE INDEX IF NOT EXISTS stock_event_item_idx ON tcg_stock_events(extraction_item_id);
CREATE INDEX IF NOT EXISTS stock_event_supersedes_idx ON tcg_stock_events(supersedes_event_id);
CREATE INDEX IF NOT EXISTS stock_plan_offer_idx ON tcg_restock_plans(offer_id,source_event_id);
CREATE INDEX IF NOT EXISTS stock_plan_event_idx ON tcg_restock_plans(source_event_id);
CREATE INDEX IF NOT EXISTS stock_publication_state_idx ON tcg_stock_publications(state,created_at,id);
CREATE INDEX IF NOT EXISTS stock_control_baseline_idx ON tcg_stock_control(baseline_publication_id);
CREATE INDEX IF NOT EXISTS stock_control_approval_idx ON tcg_stock_control(approved_publication_id);
CREATE INDEX IF NOT EXISTS stock_inbox_state_idx ON tcg_stock_inbox(state,seq);
CREATE INDEX IF NOT EXISTS stock_target_reservation_idx ON tcg_distribution_targets(active_publication_id);
$ddl$;
        FOREACH relation_name IN ARRAY ARRAY['tcg_stock_offers','tcg_stock_events','tcg_restock_plans','tcg_stock_publications','tcg_stock_control','tcg_stock_inbox'] LOOP
            IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass(format('%I.%I',ns,relation_name)) AND tgname='stock_row_guard') THEN
                EXECUTE format('CREATE TRIGGER stock_row_guard BEFORE INSERT OR UPDATE OR DELETE ON %I.%I FOR EACH ROW EXECUTE FUNCTION %I.stock_row_guard()',ns,relation_name,ns);
            END IF;
        END LOOP;
        IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass(format('%I.tcg_distribution_targets',ns)) AND tgname='stock_target_guard') THEN
            EXECUTE format('CREATE TRIGGER stock_target_guard BEFORE UPDATE OR DELETE ON %I.tcg_distribution_targets FOR EACH ROW EXECUTE FUNCTION %I.stock_target_guard()',ns,ns);
        END IF;
        IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass(format('%I.source_messages',ns)) AND tgname='stock_source_guard') THEN
            EXECUTE format('CREATE TRIGGER stock_source_guard BEFORE DELETE ON %I.source_messages FOR EACH ROW EXECUTE FUNCTION %I.stock_source_guard()',ns,ns);
        END IF;
        FOREACH relation_name IN ARRAY ARRAY['tcg_stock_offers','tcg_stock_events','tcg_restock_plans','tcg_stock_publications','tcg_stock_control','tcg_stock_inbox','source_messages','extraction_items','extraction_jobs','tcg_distribution_targets'] LOOP
            IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass(format('%I.%I',ns,relation_name)) AND tgname='stock_deferred_guard') THEN
                EXECUTE format('CREATE CONSTRAINT TRIGGER stock_deferred_guard AFTER INSERT OR UPDATE ON %I.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION %I.stock_deferred_guard()',ns,relation_name,ns);
            END IF;
        END LOOP;
        EXECUTE $ddl$
INSERT INTO tcg_stock_control(id,rollout_id,mode) VALUES(1,gen_random_uuid(),'legacy') ON CONFLICT(id) DO NOTHING;
$ddl$;
        PERFORM set_config('search_path',saved_path,true);
    END LOOP;
END $migration$;
