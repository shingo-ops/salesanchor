CREATE SCHEMA t;
CREATE TABLE t.source_messages(id uuid PRIMARY KEY, supplier_channel_id uuid, received_at timestamptz);
CREATE TABLE t.extraction_jobs(id uuid PRIMARY KEY, source_message_id uuid);
CREATE TABLE t.extraction_items(id uuid PRIMARY KEY, extraction_job_id uuid, gone boolean NOT NULL DEFAULT false);
CREATE TABLE t.analysis_results(id uuid PRIMARY KEY, extraction_item_id uuid UNIQUE, product_id int, condition_id int, pid_resolved boolean DEFAULT true, computed_at timestamptz DEFAULT '2026-10-10', is_current boolean NOT NULL DEFAULT true, updated_at timestamptz DEFAULT now(), tag text);
CREATE TABLE t.analysis_soldout_extra_targets(id serial PRIMARY KEY, analysis_result_id uuid REFERENCES t.analysis_results(id), product_id int, condition_id int);
CREATE FUNCTION add_post(ch uuid, hrs numeric) RETURNS uuid LANGUAGE plpgsql AS $$ DECLARE s uuid := gen_random_uuid(); j uuid := gen_random_uuid(); BEGIN
 INSERT INTO t.source_messages VALUES (s, ch, now() - make_interval(secs => hrs*3600)); INSERT INTO t.extraction_jobs VALUES (j, s); RETURN j; END $$;
CREATE FUNCTION add_row(j uuid, p int, c int, tag text) RETURNS uuid LANGUAGE plpgsql AS $$ DECLARE i uuid := gen_random_uuid(); r uuid := gen_random_uuid(); BEGIN
 INSERT INTO t.extraction_items(id, extraction_job_id) VALUES (i, j); INSERT INTO t.analysis_results(id, extraction_item_id, product_id, condition_id, tag) VALUES (r, i, p, c, tag); RETURN r; END $$;
CREATE FUNCTION chan_of(j uuid) RETURNS uuid LANGUAGE sql AS $$ SELECT sm.supplier_channel_id FROM t.extraction_jobs ej JOIN t.source_messages sm ON sm.id=ej.source_message_id WHERE ej.id=j $$;
