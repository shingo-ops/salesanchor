-- 01_precheck.sql (READ-ONLY)
-- 復活止めの既存データ修正 (確認済 2 件) の事前確認。件数・状態が期待と違えば RAISE して止まる。
-- 対象 DB jarvis_db / schema public。根拠一覧: /tmp/CC報告ファイル/revival_guard/confirmed.tsv (docs/handoff/revival-guard/recon.md §5)。
\set ON_ERROR_STOP on
BEGIN READ ONLY;
DO $do$
DECLARE
  ids uuid[] := ARRAY['349eaef0-1958-4a82-80eb-74d9c6fe5212','f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe']::uuid[];
  n int; bad int; r record;
BEGIN
  SELECT count(*) INTO n FROM public.analysis_results WHERE id = ANY(ids);
  IF n <> 2 THEN RAISE EXCEPTION 'GUARD 対象行 % 件 (期待 2)', n; END IF;
  -- 期待の状態: 現行 / 商品 / 状態 / computed_at / updated_at が記録どおり
  SELECT count(*) INTO bad FROM public.analysis_results ar
   WHERE ar.id = ANY(ids) AND NOT (
     ar.is_current AND ar.pid_resolved
     AND ((ar.id = '349eaef0-1958-4a82-80eb-74d9c6fe5212' AND ar.product_id = 440569 AND ar.condition_id = 17
            AND ar.computed_at = '2026-10-18 00:08:01.954577+00' AND ar.updated_at = '2026-10-18 00:08:02.033735+00')
       OR (ar.id = 'f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe' AND ar.product_id = 458213 AND ar.condition_id = 12
            AND ar.computed_at = '2026-10-18 00:21:58.361305+00' AND ar.updated_at = '2026-10-18 00:21:58.428487+00')));
  IF bad <> 0 THEN RAISE EXCEPTION 'GUARD % 件が記録した状態と違う', bad; END IF;
  -- 同じ仕入元に、より新しい投稿で同じ商品の現行の行がある (= 配信が二重になっている)
  FOR r IN
    SELECT ar.id,
           (SELECT count(*) FROM public.analysis_results a2
              JOIN public.extraction_items e2 ON e2.id = a2.extraction_item_id
              JOIN public.extraction_jobs j2 ON j2.id = e2.extraction_job_id
              JOIN public.source_messages s2 ON s2.id = j2.source_message_id
             WHERE s2.supplier_channel_id = sm.supplier_channel_id AND a2.product_id = ar.product_id
               AND a2.pid_resolved AND a2.is_current AND s2.received_at > sm.received_at) AS newer_current
      FROM public.analysis_results ar
      JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
      JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
      JOIN public.source_messages sm ON sm.id = ej.source_message_id
     WHERE ar.id = ANY(ids) LOOP
    IF r.newer_current < 1 THEN RAISE EXCEPTION 'GUARD % : 新しい投稿の同商品の現行行が無い', r.id; END IF;
    RAISE NOTICE 'precheck ok % newer_current_rows=%', r.id, r.newer_current;
  END LOOP;
  RAISE NOTICE 'PRECHECK OK: 2 rows';
END
$do$;
SELECT id, product_id, condition_id, is_current, computed_at, updated_at FROM public.analysis_results
 WHERE id IN ('349eaef0-1958-4a82-80eb-74d9c6fe5212','f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe') ORDER BY id;
ROLLBACK;
