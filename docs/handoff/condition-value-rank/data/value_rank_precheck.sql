-- 状態の価値順（ADR-1023）値の投入の precheck（読み取り）。
-- 期待: COLUMNS|2・TARGET_ROWS|11・ALREADY_SET|0・PRECHECK_DONE
SELECT 'COLUMNS|' || count(*) FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'line_conditions' AND column_name IN ('value_group', 'value_rank');
SELECT 'VIEW_HAS_COLUMN|' || count(*) FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'conditions' AND column_name IN ('value_group', 'value_rank');
SELECT 'TARGET_ROWS|' || count(*) FROM public.line_conditions
 WHERE code IN ('CN0003','CN0004','CN0005','CN0006','CN20261008072213','CN0001','CN0002','CN0009','CN0007','CN0010','CN0013') AND tenant_id IS NULL;
SELECT 'ALREADY_SET|' || count(*) FROM public.line_conditions
 WHERE code IN ('CN0003','CN0004','CN0005','CN0006','CN20261008072213','CN0001','CN0002','CN0009','CN0007','CN0010','CN0013') AND tenant_id IS NULL AND value_rank IS NOT NULL;
SELECT 'PRECHECK_DONE';
