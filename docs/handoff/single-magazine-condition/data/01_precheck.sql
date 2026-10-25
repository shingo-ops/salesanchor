-- 状態「雑誌付き」(CN0027・シングル系) 事前確認（読むだけ）。本番への実行は PO の `!`（担当は実行しない）。
-- 期待: PRECHECK_OK が 8 行（single_5rows・single_kubun・code_CN0027_unused・canonical_absent_in_single・CN0025_one・unit 17=Booklet・check_allows_single・products_counted）。ROW・ROWFULL・CONSTRAINT・FK・PRODUCTS は情報として出る。1つでも違えば止まる（1/0 で失敗させる）。
\set ON_ERROR_STOP on
SET default_transaction_read_only = on;
-- 1. 状態の今の行（適用後に 03_verify の ROW 行と突き合わせる基準）
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
-- 1b. 群 single の既存 5 行と CN0025 の全列（K3・K4 の基準。03_verify の ROWFULL 行と手で突き合わせる）
SELECT 'ROWFULL|' || t.id || '|' || md5(to_jsonb(t)::text) || '|' || to_jsonb(t)::text
  FROM public.line_conditions t WHERE t.value_group = 'single' OR t.code = 'CN0025' ORDER BY t.id;
-- 2. 群 single が 5 行で、canonical が PSA10 / PSA9 / PSA8 / PSA7以下 / Single
SELECT CASE WHEN count(*) = 5
             AND count(*) FILTER (WHERE canonical IN ('PSA10', 'PSA9', 'PSA8', 'PSA7以下', 'Single')) = 5
             AND count(DISTINCT canonical) = 5
            THEN 'PRECHECK_OK single_5rows 5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single';
-- 2b. 群 single の既存行が全部 app_kubun 'シングル系'
SELECT CASE WHEN count(*) = 5 AND count(*) FILTER (WHERE app_kubun = 'シングル系') = 5
            THEN 'PRECHECK_OK single_kubun 5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single';
-- 3. code CN0027 が未使用（CN+14桁の日時の値もあるため、最大値からの採番はしない）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK code_CN0027_unused 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0027';
-- 4. canonical「雑誌付き」が群 single に無い（群の中で canonical は重ならないこと）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK canonical_absent_in_single 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single' AND canonical = '雑誌付き';
-- 4b. 比べる相手の CN0025（promo_pack の雑誌付き）が 1 行ある
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK CN0025_one 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0025' AND canonical = '雑誌付き' AND value_group = 'promo_pack';
-- 5. 単位の辞書: line_units の id 17 が Booklet
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK unit 17=Booklet' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_units WHERE id = 17 AND canonical = 'Booklet';
-- 6. value_group の CHECK が single を許している（名前は固定にしない）
SELECT 'CONSTRAINT|' || conname || '|' || pg_get_constraintdef(oid)
  FROM pg_constraint WHERE conrelid = 'public.line_conditions'::regclass AND contype = 'c';
SELECT CASE WHEN count(*) >= 1 THEN 'PRECHECK_OK check_allows_single' ELSE (1 / (count(*) - count(*)))::text END
  FROM pg_constraint
 WHERE conrelid = 'public.line_conditions'::regclass AND contype = 'c'
   AND pg_get_constraintdef(oid) LIKE '%value_group%' AND pg_get_constraintdef(oid) LIKE '%single%';
-- 7. line_conditions.id を外部キーで参照している表（情報。04_rollback で削除してよいかに関わる）
SELECT 'FK|' || c.conrelid::regclass || '|' || c.conname || '|' || pg_get_constraintdef(c.oid)
  FROM pg_constraint c WHERE c.contype = 'f' AND c.confrelid = 'public.line_conditions'::regclass ORDER BY 1;
SELECT 'PRECHECK_INFO fk_to_line_conditions ' || count(*)
  FROM pg_constraint c WHERE c.contype = 'f' AND c.confrelid = 'public.line_conditions'::regclass;
-- 8. 解析結果の表（analysis_results）が line_conditions を外部キーで参照している数（0 なら参照なし）
SELECT 'PRECHECK_INFO analysis_results_fk_to_line_conditions ' || count(*)
  FROM pg_constraint c
 WHERE c.contype = 'f' AND c.confrelid = 'public.line_conditions'::regclass AND c.conrelid = to_regclass('public.analysis_results');
-- 9. products の件数（K5 の基準。03_verify の PRODUCTS 行と突き合わせる）
SELECT 'PRODUCTS|' || count(*) FROM public.products;
SELECT CASE WHEN count(*) > 0 THEN 'PRECHECK_OK products_counted' ELSE (1 / (count(*) - count(*)))::text END FROM public.products;
