-- 現行 (origin/main 93a06a59b の tcg_analyzer_svc.py:2019-2093 の SQL。スキーマ名 t・バインドを関数引数に置換しただけ)
CREATE OR REPLACE FUNCTION merge_old(p_job uuid, p_channel uuid, p_pids int[], p_cids int[]) RETURNS void LANGUAGE sql AS $f$
WITH touched_triples AS (
    SELECT DISTINCT ar.product_id, ar.condition_id
    FROM t.analysis_results ar
    JOIN t.extraction_items ei ON ei.id = ar.extraction_item_id AND NOT ei.gone
    WHERE ei.extraction_job_id = p_job AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL
    UNION
    SELECT x.product_id, x.condition_id FROM unnest(p_pids, p_cids) AS x(product_id, condition_id)
    UNION
    SELECT et.product_id, et.condition_id
    FROM t.analysis_soldout_extra_targets et
    JOIN t.analysis_results ar ON ar.id = et.analysis_result_id
    JOIN t.extraction_items ei ON ei.id = ar.extraction_item_id AND NOT ei.gone
    WHERE ei.extraction_job_id = p_job
),
candidates AS (
    SELECT ar.id AS id, ar.product_id, ar.condition_id, sm.received_at, ar.computed_at, ej.id AS job_id
    FROM t.analysis_results ar
    JOIN t.extraction_items ei ON ei.id = ar.extraction_item_id AND NOT ei.gone
    JOIN t.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN t.source_messages sm ON sm.id = ej.source_message_id
    WHERE sm.supplier_channel_id = p_channel AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL
      AND EXISTS (SELECT 1 FROM touched_triples tt WHERE tt.product_id = ar.product_id AND tt.condition_id = ar.condition_id)
    UNION ALL
    SELECT NULL::uuid AS id, et.product_id, et.condition_id, sm.received_at, ar.computed_at, ej.id AS job_id
    FROM t.analysis_soldout_extra_targets et
    JOIN t.analysis_results ar ON ar.id = et.analysis_result_id
    JOIN t.extraction_items ei ON ei.id = ar.extraction_item_id AND NOT ei.gone
    JOIN t.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN t.source_messages sm ON sm.id = ej.source_message_id
    WHERE sm.supplier_channel_id = p_channel
      AND EXISTS (SELECT 1 FROM touched_triples tt WHERE tt.product_id = et.product_id AND tt.condition_id = et.condition_id)
),
job_rank AS (
    SELECT c.product_id, c.condition_id, c.job_id, MAX(c.received_at) AS received_at, MAX(c.computed_at) AS max_computed_at
    FROM candidates c GROUP BY c.product_id, c.condition_id, c.job_id
),
top_job AS (
    SELECT DISTINCT ON (jr.product_id, jr.condition_id) jr.product_id, jr.condition_id, jr.job_id
    FROM job_rank jr
    ORDER BY jr.product_id, jr.condition_id, jr.received_at DESC, jr.max_computed_at DESC, jr.job_id DESC
),
ranked AS (
    SELECT c.id, (c.job_id = t.job_id) AS should_be_current
    FROM candidates c JOIN top_job t ON t.product_id = c.product_id AND t.condition_id = c.condition_id
)
UPDATE t.analysis_results ar_target
SET is_current = ranked.should_be_current, updated_at = NOW()
FROM ranked
WHERE ar_target.id = ranked.id AND ar_target.is_current IS DISTINCT FROM ranked.should_be_current
$f$;
