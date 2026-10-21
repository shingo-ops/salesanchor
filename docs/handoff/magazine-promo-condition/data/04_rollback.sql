-- 状態「雑誌付き」(CN0025) 戻し。本番での実行は PO の `!`（担当は実行しない）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN         : psql -v end=ROLLBACK -f 04_rollback.sql              （無効化だけを試して ROLLBACK。K7）
--   無効化して終わる: psql -v end=COMMIT   -f 04_rollback.sql              （既定の戻し。CN0025 を is_active=false にする）
--   消すところまで  : psql -v end=COMMIT -v del=1 -f 04_rollback.sql       （line_conditions を指す参照が 0 件のときだけ行を消す。1 件でもあれば 1/0 で止まる）
-- どの場合も、このあと保留 3 行を再解析して未開封へ戻す（台本は CC報告ファイル-keep の magazine3/ を戻し用に作り直す）。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;
-- 1. 無効にする（外部キーがあっても安全な戻し）
WITH u AS (
    UPDATE public.line_conditions SET is_active = false, updated_at = NOW()
     WHERE code = 'CN0025' AND canonical = '雑誌付き' AND value_group = 'promo_pack' AND is_active
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK conditions deactivated|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;

-- 2. line_conditions.id を外部キーで参照している全部の表から、CN0025 を指す行を数える（ON DELETE CASCADE / SET NULL で消えるものも含む）
DO $$
DECLARE r record; n bigint; total bigint := 0; cid int;
BEGIN
  SELECT id INTO cid FROM public.line_conditions WHERE code = 'CN0025';
  IF cid IS NULL THEN RAISE EXCEPTION 'CN0025 が無い'; END IF;
  FOR r IN SELECT c.conrelid::regclass AS tbl, a.attname AS col
             FROM pg_constraint c JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
            WHERE c.contype = 'f' AND c.confrelid = 'public.line_conditions'::regclass AND array_length(c.conkey, 1) = 1
  LOOP
    EXECUTE format('SELECT count(*) FROM %s WHERE %I = $1', r.tbl, r.col) INTO n USING cid;
    RAISE NOTICE 'REF|%|%|%', r.tbl, r.col, n;
    total := total + n;
  END LOOP;
  PERFORM set_config('rb.refs', total::text, true);
END $$;
SELECT 'ROLLBACK_INFO refs ' || current_setting('rb.refs');
SELECT current_setting('rb.refs')::bigint = 0 AS refs_zero \gset

-- 3. 行を消す（-v del=1 を付けたときだけ。参照が 0 件でなければ 1/0 で止まる）
\if :{?del}
  \if :refs_zero
    WITH d AS (
        DELETE FROM public.line_conditions WHERE code = 'CN0025' AND canonical = '雑誌付き' AND value_group = 'promo_pack' AND NOT is_active RETURNING id
    )
    SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK conditions deleted|1' ELSE (1 / (count(*) - count(*)))::text END FROM d;
  \else
    \echo '参照が 0 件でないので行を消さない（無効化のまま止める）'
    SELECT 1 / 0;
  \endif
\else
  SELECT 'ROLLBACK delete skipped (無効化のみ)';
\endif

-- 4. 既存 3 行は変わらない
SELECT CASE WHEN count(*) = 3 THEN 'ROLLBACK_CHECK_OK existing_rows 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (id, code, canonical, priority, value_rank, is_active) IN
       ((60, 'CN0020', '未開封', 10, 1, true), (61, 'CN0021', '開封済み', 2, 2, true), (62, 'CN0022', 'PSA10', 2, 3, true));

:end;
SELECT 'ROLLBACK_END';
