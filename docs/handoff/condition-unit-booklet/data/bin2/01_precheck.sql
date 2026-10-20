-- ADR-1035 便2 事前確認（読むだけ）。本番への実行は Opus（担当は実行しない）。
-- 期待: 全部 PRECHECK_OK。1つでも違えば止まる（1/0 で失敗させる）。
-- 前提: コード反映（PR マージ・デプロイ・migration 20261020_100000 の適用）の後に流す。
\set ON_ERROR_STOP on
-- 1. 状態の今の行（適用後に 03_verify の ROW 行と突き合わせる基準）
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
SELECT 'PRECHECK_INFO conditions ' || count(*) || ' max_code ' || coalesce(max(code) FILTER (WHERE code ~ '^CN[0-9]+$'), 'NONE') FROM public.line_conditions;
-- 2. 02_apply が付ける code（固定: CN0023=With booklet・CN0024=Without booklet）。表示するだけ。重なり確認は次の 3b
--    （line_conditions.code には画面が自動で作る CN+14 桁の日時の値もあるため、整数に変換する採番はしない）
SELECT 'PRECHECK_INFO next_codes CN0023 CN0024';
-- 3. 英語名が重ならない（recon 事実 2）
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK canonical_unused 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE canonical IN ('With booklet', 'Without booklet');
-- 3b. 固定の 2 つの code（CN0023・CN0024）が未使用
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK next_codes_unused 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code IN ('CN0023', 'CN0024');
-- 4. CHECK 制約の名前と中身（migration で作り直した制約が booklet を許していること。名前は固定にしない）
SELECT 'CONSTRAINT|' || conname || '|' || pg_get_constraintdef(oid)
  FROM pg_constraint WHERE conrelid = 'public.line_conditions'::regclass AND contype = 'c';
SELECT CASE WHEN count(*) >= 1 THEN 'PRECHECK_OK check_allows_booklet' ELSE (1 / (count(*) - count(*)))::text END
  FROM pg_constraint
 WHERE conrelid = 'public.line_conditions'::regclass AND contype = 'c'
   AND pg_get_constraintdef(oid) LIKE '%value_group%' AND pg_get_constraintdef(oid) LIKE '%booklet%';
-- 5. 単位の辞書: line_units の id 17 が Booklet
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK unit 17=Booklet' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_units WHERE id = 17 AND canonical = 'Booklet';
-- 6. 区分マスタに PC_BOOKLET・ブックレット系が無い
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK category_absent 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories WHERE code = 'PC_BOOKLET' OR kubun_type = 'ブックレット系';
-- 7. 商品 440415 の区分が 2（シングル系）
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK product_440415_category_2 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products WHERE id = 440415 AND product_category_id = 2;
-- 8. 再解析の対象 job の数（05_target_jobs と同じ条件）
SELECT 'PRECHECK_INFO target_jobs ' || count(DISTINCT j.id) || ' rows ' || count(*)
  FROM public.analysis_results ar
  JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
  JOIN public.extraction_jobs j ON j.id = ei.extraction_job_id
 WHERE ar.is_current AND j.prompt_version LIKE 'v102:%' AND ar.product_id = 440415;
