-- ADR-1035 便2 再解析の対象 job を数える（読むだけ）。
-- 対象: 商品 440415 の v102 の現行行を持つ job だけ。外す商品は無い（便1 の入れ忘れの再発防止: 条件は商品 1 つだけで、ほかの商品を足さない）。
-- 再解析はこの SQL では行わない。
SELECT 'TARGET_JOBS|' || count(DISTINCT j.id) || '|rows=' || count(*)
  FROM public.analysis_results ar
  JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
  JOIN public.extraction_jobs j ON j.id = ei.extraction_job_id
 WHERE ar.is_current AND j.prompt_version LIKE 'v102:%'
   AND ar.product_id = 440415;
SELECT 'TARGET_JOB_ID|' || j.id
  FROM public.analysis_results ar
  JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
  JOIN public.extraction_jobs j ON j.id = ei.extraction_job_id
 WHERE ar.is_current AND j.prompt_version LIKE 'v102:%'
   AND ar.product_id = 440415
 GROUP BY j.id ORDER BY j.id;
