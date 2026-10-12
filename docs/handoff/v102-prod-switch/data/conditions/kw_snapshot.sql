-- 再解析の前後比較用（読み取り）。対象3ジョブの analysis_results 全行（is_current を含む）。原文は出さない。
-- 列: job8|item8|line_start|line_end|is_current|product_id|condition_canonical|condition_basis|unit_canonical|price_normalized|quantity_normalized|needs_review|review_reasons|status|exclusion|engine_version|computed_at
SELECT left(ej.id::text, 8) || '|' || left(ei.id::text, 8) || '|' || ei.line_start || '|' || COALESCE(ei.line_end::text, '') || '|' || ar.is_current || '|' || COALESCE(ar.product_id::text, '') || '|' || COALESCE(ar.condition_canonical, '') || '|' || COALESCE(ar.condition_basis, '') || '|' || COALESCE(ar.unit_canonical, '') || '|' || COALESCE(ar.price_normalized::text, '') || '|' || COALESCE(ar.quantity_normalized::text, '') || '|' || COALESCE(ar.needs_review::text, '') || '|' || COALESCE(ar.review_reasons, '') || '|' || COALESCE(ar.status, '') || '|' || COALESCE(ar.exclusion, '') || '|' || COALESCE(ar.engine_version, '') || '|' || ar.computed_at
  FROM public.analysis_results ar
  JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
  JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
 WHERE ej.id IN ('6b415ffa-82e3-498d-8cef-b0c072950098', 'b4605ec5-679e-454b-b109-26c7f3e02fcf', 'fda77ba1-11c0-4b31-a765-73682bb7b9c6')
 ORDER BY ej.id, ei.line_start, ei.id, ar.computed_at;
