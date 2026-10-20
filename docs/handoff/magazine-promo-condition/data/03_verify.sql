-- 状態「雑誌付き」(CN0025) 確認（読むだけ）。COMMIT の後に流す。全部 VERIFY_OK なら期待どおり。
-- ROWFULL 行は 01_precheck.sql の ROWFULL 行と同じ書式。id60/61/62 の行が前後で同じであること（K2）を、md5 を手で突き合わせて確かめる。
\set ON_ERROR_STOP on
SET default_transaction_read_only = on;
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
SELECT 'ROWFULL|' || t.id || '|' || md5(to_jsonb(t)::text) || '|' || to_jsonb(t)::text
  FROM public.line_conditions t WHERE t.id IN (60, 61, 62) ORDER BY t.id;
-- K1: 群 promo_pack が 4 行
SELECT CASE WHEN count(*) = 4 THEN 'VERIFY_OK promo_pack_rows 4' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'promo_pack';
-- K1: CN0025 の値
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK CN0025 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE code = 'CN0025' AND canonical = '雑誌付き' AND app_kubun = 'プロモパック系' AND is_active AND priority = 2
   AND search_kw = '雑誌[\s　]*(付き|つき)' AND exclude_kw = '' AND match_type = 'REGEX' AND effect = 'OUTPUT'
   AND unit_id = 17 AND value_group = 'promo_pack' AND value_rank = 4;
-- K1: 単位 17 が Booklet
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK unit_Booklet 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions c JOIN public.line_units u ON u.id = c.unit_id
 WHERE c.code = 'CN0025' AND u.id = 17 AND u.canonical = 'Booklet';
-- K2: 既存 3 行の主な値（01_precheck の控えと同じ値）。全列の一致は ROWFULL の md5 を手で突き合わせる
SELECT CASE WHEN count(*) = 3 THEN 'VERIFY_OK existing_rows 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (id, code, canonical, priority, value_rank, is_active) IN
       ((60, 'CN0020', '未開封', 10, 1, true), (61, 'CN0021', '開封済み', 2, 2, true), (62, 'CN0022', 'PSA10', 2, 3, true));
-- 群の中で canonical が重ならない
SELECT CASE WHEN count(*) = count(DISTINCT canonical) AND count(*) = 4 THEN 'VERIFY_OK canonical_unique 4' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'promo_pack' AND is_active;
