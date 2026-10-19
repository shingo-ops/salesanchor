-- ADR-1035 便1 再解析の対象 job を数える（読むだけ）。
-- 対象: 状態 22・21・44・60・61・20 のどれかが付いた v102 の現行行を持つ job。再解析はこの SQL では行わない。
SELECT 'TARGET_JOBS|' || count(DISTINCT j.id) || '|rows=' || count(*)
  FROM public.analysis_results ar
  JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
  JOIN public.extraction_jobs j ON j.id = ei.extraction_job_id
 WHERE ar.is_current AND j.prompt_version LIKE 'v102:%'
   AND ar.condition_id IN (22, 21, 44, 60, 61, 20);
SELECT 'BY_CONDITION|' || ar.condition_id || '|jobs=' || count(DISTINCT j.id) || '|rows=' || count(*)
  FROM public.analysis_results ar
  JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
  JOIN public.extraction_jobs j ON j.id = ei.extraction_job_id
 WHERE ar.is_current AND j.prompt_version LIKE 'v102:%'
   AND ar.condition_id IN (22, 21, 44, 60, 61, 20)
 GROUP BY ar.condition_id ORDER BY ar.condition_id;
