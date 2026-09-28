-- 受信時刻（received_at）を採用本文の投稿時刻（line_posted_at）にそろえ、
-- ADR-158 の is_current を正しい投稿順で選び直す。
-- 詳細: docs/handoff/fix-received-at-latest/design.md
-- 冪等: 2回目以降は更新0行

UPDATE public.source_messages
   SET received_at = line_posted_at
 WHERE line_posted_at IS NOT NULL
   AND received_at IS DISTINCT FROM line_posted_at;

WITH ranked AS (
    SELECT ar.id,
           (ROW_NUMBER() OVER (
               PARTITION BY sm.supplier_channel_id, ar.product_id, ar.condition_id
               ORDER BY sm.received_at DESC NULLS LAST, ar.computed_at DESC
           ) = 1) AS should_be_current
      FROM public.analysis_results ar
      JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
      JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
      JOIN public.source_messages sm ON sm.id = ej.source_message_id
     WHERE sm.supplier_channel_id IS NOT NULL
       AND ar.pid_resolved = TRUE
       AND ar.product_id IS NOT NULL
)
UPDATE public.analysis_results ar_target
   SET is_current = ranked.should_be_current,
       updated_at = NOW()
  FROM ranked
 WHERE ar_target.id = ranked.id
   AND ar_target.is_current IS DISTINCT FROM ranked.should_be_current;
