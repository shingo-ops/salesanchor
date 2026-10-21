-- 02_apply.sql (WRITES; PO の GO #番号 が必要)
-- 確認済 2 件の is_current を FALSE にする。変更前の値は audit_log (merge_id revival-guard-20261019) に残す。
-- 対象 DB jarvis_db / schema public。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '120s';
DO $do$
DECLARE
  ids uuid[] := ARRAY['349eaef0-1958-4a82-80eb-74d9c6fe5212','f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe']::uuid[];
  before_rows jsonb; c int;
BEGIN
  -- 1. 件数の守り: 対象は現行の 2 行ちょうど
  SELECT count(*), jsonb_agg(jsonb_build_object('id', id::text, 'from', is_current, 'to', false, 'old_updated_at', updated_at,
                                              'product_id', product_id, 'condition_id', condition_id) ORDER BY id::text)
    INTO c, before_rows FROM public.analysis_results WHERE id = ANY(ids) AND is_current;
  IF c <> 2 THEN RAISE EXCEPTION 'GUARD 現行の対象行 % 件 (期待 2)', c; END IF;
  -- 2. 更新 (updated_at は merge と同じく NOW())
  UPDATE public.analysis_results SET is_current = FALSE, updated_at = NOW() WHERE id = ANY(ids) AND is_current;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 2 THEN RAISE EXCEPTION 'UPDATE % 件 (期待 2)', c; END IF;
  -- 3. 監査行 (巻き戻し用に id と変更前の値を持つ)
  INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
  VALUES ('analysis_results', gen_random_uuid(), 'UPDATE', 'claude-opus (PO承認待ち 2026-10-19 revival-guard)',
          before_rows::text,
          jsonb_build_object('merge_id', 'revival-guard-20261019', 'counts', jsonb_build_object('is_current_flips', 2),
                             'ids', jsonb_build_object('is_current_flips', before_rows))::text);
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 1 THEN RAISE EXCEPTION 'audit_log insert % 件 (期待 1)', c; END IF;
  RAISE NOTICE 'DONE: 2 rows set FALSE, 1 audit_log row';
END
$do$;
SELECT id, is_current, updated_at FROM public.analysis_results
 WHERE id IN ('349eaef0-1958-4a82-80eb-74d9c6fe5212','f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe') ORDER BY id;
COMMIT;
