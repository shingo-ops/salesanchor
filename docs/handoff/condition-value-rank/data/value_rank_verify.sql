-- 状態の価値順（ADR-1023）値の投入の verify（読み取り）。期待: 11 行。
SELECT 'ROW|' || code || '|' || canonical || '|' || COALESCE(value_group, 'NULL') || '|' || COALESCE(value_rank::text, 'NULL')
  FROM public.line_conditions WHERE value_rank IS NOT NULL AND tenant_id IS NULL ORDER BY value_group, value_rank;
SELECT 'ROWS|' || count(*) FROM public.line_conditions WHERE value_rank IS NOT NULL AND tenant_id IS NULL;
SELECT 'VERIFY_DONE';
