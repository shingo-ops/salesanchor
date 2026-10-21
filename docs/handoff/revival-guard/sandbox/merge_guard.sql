-- merge_guard: 現行 merge_old に「復活止め」を足した案。スキーマ名 t・バインドを関数引数にしてある。
-- 追加引数 p_prior_pids/p_prior_cids = 「この付け直しの前に p_job の行で is_current=TRUE だった (product,condition) の組」。
--   NULL = 呼び出し側が控えを取っていない（初回の解析・人の直し・取り消し）→ 行の今の is_current を「前から現行」とみなす。
-- p_guard=false なら復活止めを切る (呼び出し側ごとに切れる。現行と同じ動きになる)。
-- 規則: 組の最新投稿の行でも、(i) 同じ仕入元の「より新しい投稿」に同じ商品の行(仮の行を含む)が無い、または
--        (ii) 付け直しの前から現行だった、のどちらでもなければ FALSE にする。すでに現行の行はこの規則では落とさない。
CREATE OR REPLACE FUNCTION merge_guard(p_job uuid, p_channel uuid, p_pids int[], p_cids int[],
                                        p_prior_pids int[] DEFAULT NULL, p_prior_cids int[] DEFAULT NULL,
                                        p_guard boolean DEFAULT true) RETURNS void LANGUAGE sql AS $f$
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
    SELECT ar.id AS id, ar.product_id, ar.condition_id, sm.received_at, ar.computed_at, ej.id AS job_id,
           CASE WHEN ej.id = p_job AND p_prior_pids IS NOT NULL
                THEN EXISTS (SELECT 1 FROM unnest(p_prior_pids, p_prior_cids) AS pr(product_id, condition_id)
                              WHERE pr.product_id = ar.product_id AND pr.condition_id IS NOT DISTINCT FROM ar.condition_id)
                ELSE ar.is_current END AS was_current
    FROM t.analysis_results ar
    JOIN t.extraction_items ei ON ei.id = ar.extraction_item_id AND NOT ei.gone
    JOIN t.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN t.source_messages sm ON sm.id = ej.source_message_id
    WHERE sm.supplier_channel_id = p_channel AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL
      AND EXISTS (SELECT 1 FROM touched_triples tt WHERE tt.product_id = ar.product_id AND tt.condition_id = ar.condition_id)
    UNION ALL
    SELECT NULL::uuid AS id, et.product_id, et.condition_id, sm.received_at, ar.computed_at, ej.id AS job_id, TRUE AS was_current
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
    SELECT c.id,
           (c.job_id = t.job_id)
           AND (NOT p_guard OR c.was_current
                OR NOT EXISTS (
                    SELECT 1 FROM t.analysis_results ar2
                    JOIN t.extraction_items ei2 ON ei2.id = ar2.extraction_item_id AND NOT ei2.gone
                    JOIN t.extraction_jobs ej2 ON ej2.id = ei2.extraction_job_id
                    JOIN t.source_messages sm2 ON sm2.id = ej2.source_message_id
                    WHERE sm2.supplier_channel_id = p_channel AND ar2.pid_resolved = TRUE
                      AND ar2.product_id = c.product_id AND sm2.received_at > c.received_at
                    UNION ALL
                    SELECT 1 FROM t.analysis_soldout_extra_targets et2
                    JOIN t.analysis_results ar3 ON ar3.id = et2.analysis_result_id
                    JOIN t.extraction_items ei3 ON ei3.id = ar3.extraction_item_id AND NOT ei3.gone
                    JOIN t.extraction_jobs ej3 ON ej3.id = ei3.extraction_job_id
                    JOIN t.source_messages sm3 ON sm3.id = ej3.source_message_id
                    WHERE sm3.supplier_channel_id = p_channel AND et2.product_id = c.product_id AND sm3.received_at > c.received_at
                )) AS should_be_current
    FROM candidates c JOIN top_job t ON t.product_id = c.product_id AND t.condition_id = c.condition_id
)
UPDATE t.analysis_results ar_target
SET is_current = ranked.should_be_current, updated_at = NOW()
FROM ranked
WHERE ar_target.id = ranked.id AND ar_target.is_current IS DISTINCT FROM ranked.should_be_current
$f$;
