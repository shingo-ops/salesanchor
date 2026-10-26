-- 状態「雑誌付き」(CN0027・シングル系) 戻し。本番での実行は PO の `!`（担当は実行しない）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN         : psql -v end=ROLLBACK -f 04_rollback.sql              （無効化だけを試して ROLLBACK。K7）
--   無効化して終わる: psql -v end=COMMIT   -f 04_rollback.sql              （既定の戻し。CN0027 を is_active=false にする）
--   消すところまで  : psql -v end=COMMIT -v del=1 -f 04_rollback.sql       （line_conditions を指す参照が 0 件のときだけ行を消す。1 件でもあれば 1/0 で止まる）
-- どの場合も、CN0027 で「雑誌付き」になった解析結果は再解析しない限りそのまま残る（必要なら対象を決めて再解析の台本を別に作る）。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;
-- 0. CN0027 以外の全行の全列を控える（取引の中だけ）
CREATE TEMP TABLE _lc_before ON COMMIT DROP AS
  SELECT id, to_jsonb(t) AS j FROM public.line_conditions t WHERE t.code <> 'CN0027';
SELECT CASE WHEN count(*) > 0 THEN 'BEFORE_OK other_rows ' || count(*) ELSE (1 / (count(*) - count(*)))::text END FROM _lc_before;

-- 1. 無効にする（外部キーがあっても安全な戻し）
WITH u AS (
    UPDATE public.line_conditions SET is_active = false, updated_at = NOW()
     WHERE code = 'CN0027' AND canonical = '雑誌付き' AND value_group = 'single' AND is_active
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK conditions deactivated|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;

-- 2. line_conditions.id を外部キーで参照している全部の表から、CN0027 を指す行を数える（ON DELETE CASCADE / SET NULL で消えるものも含む）
DO $$
DECLARE r record; n bigint; total bigint := 0; cid int;
BEGIN
  SELECT id INTO cid FROM public.line_conditions WHERE code = 'CN0027';
  IF cid IS NULL THEN RAISE EXCEPTION 'CN0027 が無い'; END IF;
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
        DELETE FROM public.line_conditions WHERE code = 'CN0027' AND canonical = '雑誌付き' AND value_group = 'single' AND NOT is_active RETURNING id
    )
    SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK conditions deleted|1' ELSE (1 / (count(*) - count(*)))::text END FROM d;
  \else
    \echo '参照が 0 件でないので行を消さない（無効化のまま止める）'
    SELECT 1 / 0;
  \endif
\else
  SELECT 'ROLLBACK delete skipped (無効化のみ)';
\endif

-- 4. CN0027 以外の行は全列が変わらない（既存 single 5 行・CN0025 を含む）
SELECT CASE WHEN count(*) = (SELECT count(*) FROM _lc_before) THEN 'ROLLBACK_CHECK_OK other_rows_unchanged ' || count(*) ELSE (1 / (count(*) - count(*)))::text END
  FROM _lc_before b JOIN public.line_conditions t ON t.id = b.id WHERE to_jsonb(t) = b.j;
SELECT CASE WHEN count(*) = 5 THEN 'ROLLBACK_CHECK_OK single_existing 5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single' AND code <> 'CN0027' AND is_active;

:end;
SELECT 'ROLLBACK_END';
