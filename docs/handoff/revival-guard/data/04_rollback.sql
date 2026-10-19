-- 04_rollback.sql (WRITES; 新しい PO 判断が必要)
-- 監査行 (merge_id revival-guard-20261019) の変更前の値 (is_current と updated_at) に、保存した 2 行だけ戻す。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '120s';
DO $do$
DECLARE a record; f jsonb; c int; seen int := 0; restored int := 0;
BEGIN
  FOR a IN SELECT id, new_values FROM public.audit_log
            WHERE table_name = 'analysis_results' AND new_values LIKE '%revival-guard-20261019%'
              AND NOT EXISTS (SELECT 1 FROM public.audit_log rb
                               WHERE rb.table_name = 'analysis_results' AND rb.changed_by = 'claude-opus (rollback; PO decision required)'
                                 AND CASE WHEN rb.new_values LIKE '{%' THEN (rb.new_values::jsonb->>'rolled_back_audit_id')::bigint END = audit_log.id)
            ORDER BY id LOOP
    seen := seen + 1;
    FOR f IN SELECT * FROM jsonb_array_elements(a.new_values::jsonb #> '{ids,is_current_flips}') LOOP
      UPDATE public.analysis_results SET is_current = (f->>'from')::boolean, updated_at = (f->>'old_updated_at')::timestamptz
       WHERE id = (f->>'id')::uuid AND is_current IS NOT DISTINCT FROM (f->>'to')::boolean;
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> 1 THEN RAISE EXCEPTION 'rollback % : % 件 (期待 1)', f->>'id', c; END IF;
      restored := restored + 1;
    END LOOP;
    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    VALUES ('analysis_results', gen_random_uuid(), 'UPDATE', 'claude-opus (rollback; PO decision required)', a.new_values,
            jsonb_build_object('rolled_back_merge_id', 'revival-guard-20261019', 'rolled_back_audit_id', a.id)::text);
  END LOOP;
  IF seen <> 1 OR restored <> 2 THEN RAISE EXCEPTION 'rollback: 監査行 % 件 / 戻した行 % 件 (期待 1 / 2)', seen, restored; END IF;
  RAISE NOTICE 'ROLLBACK DONE: 2 rows restored';
END
$do$;
SELECT id, is_current, updated_at FROM public.analysis_results
 WHERE id IN ('349eaef0-1958-4a82-80eb-74d9c6fe5212','f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe') ORDER BY id;
COMMIT;
