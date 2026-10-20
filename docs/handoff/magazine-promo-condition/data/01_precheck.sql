-- 状態「雑誌付き」(CN0025) 事前確認（読むだけ）。本番への実行は PO の `!`（担当は実行しない）。
-- 期待: PRECHECK_OK が 5 行（promo_pack・code_CN0025_unused・canonical_absent_in_promo_pack・unit 17=Booklet・check_allows_promo_pack）。ROW・CONSTRAINT・FK は情報として出る。1つでも違えば止まる（1/0 で失敗させる）。
\set ON_ERROR_STOP on
SET default_transaction_read_only = on;
-- 1. 状態の今の行（適用後に 03_verify の ROW 行と突き合わせる基準）
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
-- 1b. id60/61/62 の全列（K2 の基準。03_verify の ROWFULL 行と手で突き合わせる）
SELECT 'ROWFULL|' || t.id || '|' || md5(to_jsonb(t)::text) || '|' || to_jsonb(t)::text
  FROM public.line_conditions t WHERE t.id IN (60, 61, 62) ORDER BY t.id;
-- 2. 群 promo_pack が 3 行で、id60/61/62（CN0020/CN0021/CN0022）
SELECT CASE WHEN count(*) = 3
             AND count(*) FILTER (WHERE (id, code) IN ((60, 'CN0020'), (61, 'CN0021'), (62, 'CN0022'))) = 3
            THEN 'PRECHECK_OK promo_pack 3 (id60/61/62)' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'promo_pack';
-- 3. code CN0025 が未使用（CN+14桁の日時の値もあるため、最大値からの採番はしない）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK code_CN0025_unused 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0025';
-- 4. canonical「雑誌付き」が群 promo_pack に無い（群の中で canonical は重ならないこと）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK canonical_absent_in_promo_pack 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'promo_pack' AND canonical = '雑誌付き';
-- 5. 単位の辞書: line_units の id 17 が Booklet
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK unit 17=Booklet' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_units WHERE id = 17 AND canonical = 'Booklet';
-- 6. value_group の CHECK が promo_pack を許している（名前は固定にしない）
SELECT 'CONSTRAINT|' || conname || '|' || pg_get_constraintdef(oid)
  FROM pg_constraint WHERE conrelid = 'public.line_conditions'::regclass AND contype = 'c';
SELECT CASE WHEN count(*) >= 1 THEN 'PRECHECK_OK check_allows_promo_pack' ELSE (1 / (count(*) - count(*)))::text END
  FROM pg_constraint
 WHERE conrelid = 'public.line_conditions'::regclass AND contype = 'c'
   AND pg_get_constraintdef(oid) LIKE '%value_group%' AND pg_get_constraintdef(oid) LIKE '%promo_pack%';
-- 7. line_conditions.id を外部キーで参照している表（情報。04_rollback で削除してよいかに関わる）
SELECT 'FK|' || c.conrelid::regclass || '|' || c.conname || '|' || pg_get_constraintdef(c.oid)
  FROM pg_constraint c WHERE c.contype = 'f' AND c.confrelid = 'public.line_conditions'::regclass ORDER BY 1;
SELECT 'PRECHECK_INFO fk_to_line_conditions ' || count(*)
  FROM pg_constraint c WHERE c.contype = 'f' AND c.confrelid = 'public.line_conditions'::regclass;
-- 8. 解析結果の表（analysis_results）が line_conditions を外部キーで参照している数（0 なら参照なし）
SELECT 'PRECHECK_INFO analysis_results_fk_to_line_conditions ' || count(*)
  FROM pg_constraint c
 WHERE c.contype = 'f' AND c.confrelid = 'public.line_conditions'::regclass AND c.conrelid = 'public.analysis_results'::regclass;
