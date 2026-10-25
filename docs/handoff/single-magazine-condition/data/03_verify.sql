-- 状態「雑誌付き」(CN0027・シングル系) 確認（読むだけ）。COMMIT の後に流す。全部 VERIFY_OK なら期待どおり。
-- ROWFULL 行は 01_precheck.sql の ROWFULL 行と同じ書式。群 single の既存 5 行と CN0025 が前後で同じであること（K3・K4）を、md5 を手で突き合わせて確かめる（CN0027 の行だけが増える）。
-- PRODUCTS 行は 01_precheck.sql の PRODUCTS 行と同じ数であること（K5）を手で突き合わせる。
\set ON_ERROR_STOP on
SET default_transaction_read_only = on;
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
-- 群 single の既存 5 行・CN0025・CN0027 の全列
SELECT 'ROWFULL|' || t.id || '|' || md5(to_jsonb(t)::text) || '|' || to_jsonb(t)::text
  FROM public.line_conditions t WHERE t.value_group = 'single' OR t.code IN ('CN0025', 'CN0027') ORDER BY t.id;
-- K5: products の件数（01 の PRODUCTS 行と同じであること）
SELECT 'PRODUCTS|' || count(*) FROM public.products;
-- 群 single が 6 行
SELECT CASE WHEN count(*) = 6 THEN 'VERIFY_OK single_rows 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single';
-- CN0027 の全列の値
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK CN0027 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE code = 'CN0027' AND canonical = '雑誌付き' AND app_kubun = 'シングル系' AND is_active AND priority = 2
   AND search_kw = '雑誌(プロモ)?[\s　]*(付き|つき)|本[\s　]*(付き|つき)|付録[\s　]*(付き|つき)' AND exclude_kw = '' AND match_type = 'REGEX' AND effect = 'OUTPUT'
   AND unit_id = 17 AND value_group = 'single' AND value_rank = 6
   AND note = 'シングル系で雑誌付き・本付き・付録付きと書かれた行の状態。単位は冊（ADR-1023/1031/1035、2026-10-25 PO）';
-- 単位 17 が Booklet
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK unit_Booklet 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions c JOIN public.line_units u ON u.id = c.unit_id
 WHERE c.code = 'CN0027' AND u.id = 17 AND u.canonical = 'Booklet';
-- K4: 既存 5 行が群 single に残っている（全列の一致は ROWFULL の md5 を手で突き合わせる）
SELECT CASE WHEN count(*) = 5 AND count(DISTINCT canonical) = 5 THEN 'VERIFY_OK existing_single_rows 5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single' AND code <> 'CN0027' AND canonical IN ('PSA10', 'PSA9', 'PSA8', 'PSA7以下', 'Single');
-- K3: CN0025 が 1 行のまま（全列の一致は ROWFULL の md5）
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK CN0025_present 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0025' AND canonical = '雑誌付き' AND value_group = 'promo_pack' AND is_active;
-- 群の中で canonical が重ならない
SELECT CASE WHEN count(*) = count(DISTINCT canonical) AND count(*) = 6 THEN 'VERIFY_OK canonical_unique 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single' AND is_active;
