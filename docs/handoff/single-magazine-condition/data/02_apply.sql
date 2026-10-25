-- 状態「雑誌付き」(CN0027・シングル系) 適用。本番での実行は PO の `!`（担当は実行しない）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : psql -v end=ROLLBACK -f 02_apply.sql   （全部の件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : psql -v end=COMMIT   -f 02_apply.sql   （DRY-RUN が全部 OK だった後だけ）
-- id は identity に任せる。code は固定（CN0027。最大値からの採番はしない）。件数が違えば 1/0 で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;

-- 0. 適用前の line_conditions 全行の全列と products の件数を控える（取引の中だけ）
CREATE TEMP TABLE _lc_before ON COMMIT DROP AS
  SELECT id, to_jsonb(t) AS j FROM public.line_conditions t;
SELECT CASE WHEN count(*) = 0 THEN 'BEFORE_OK CN0027 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0027';
SELECT CASE WHEN count(*) = 5 THEN 'BEFORE_OK single 5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single';
SELECT set_config('ap.products_before', count(*)::text, true) FROM public.products;

-- 1. 状態 1 行。単位は Booklet（line_units id 17。副問い合わせで Booklet であることを確かめる）
WITH i AS (
    INSERT INTO public.line_conditions
        (code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, unit_id, note, value_group, value_rank)
    SELECT 'CN0027', '雑誌付き', 'シングル系', true, 2, '雑誌(プロモ)?[\s　]*(付き|つき)|本[\s　]*(付き|つき)|付録[\s　]*(付き|つき)', '', 'REGEX', 'OUTPUT',
           (SELECT id FROM public.line_units WHERE id = 17 AND canonical = 'Booklet'),
           'シングル系で雑誌付き・本付き・付録付きと書かれた行の状態。単位は冊（ADR-1023/1031/1035、2026-10-25 PO）',
           'single', 6
    RETURNING id, canonical, unit_id
)
SELECT CASE WHEN count(*) = 1 AND count(*) FILTER (WHERE canonical = '雑誌付き' AND unit_id = 17) = 1
            THEN 'INSERTED conditions|1' ELSE (1 / (count(*) - count(*)))::text END FROM i;

-- 2. 適用後の確認（件数が違えば失敗）
SELECT CASE WHEN count(*) = 6 THEN 'CHECK_OK single_rows 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single';
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK CN0027 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE code = 'CN0027' AND canonical = '雑誌付き' AND app_kubun = 'シングル系' AND is_active AND priority = 2
   AND search_kw = '雑誌(プロモ)?[\s　]*(付き|つき)|本[\s　]*(付き|つき)|付録[\s　]*(付き|つき)' AND exclude_kw = '' AND match_type = 'REGEX' AND effect = 'OUTPUT'
   AND unit_id = 17 AND value_group = 'single' AND value_rank = 6;
-- 適用前の全行（既存 single 5 行・CN0025 を含む）が全列同じ
SELECT CASE WHEN count(*) = (SELECT count(*) FROM _lc_before) AND count(*) > 0 THEN 'CHECK_OK other_rows_unchanged ' || count(*) ELSE (1 / (count(*) - count(*)))::text END
  FROM _lc_before b JOIN public.line_conditions t ON t.id = b.id WHERE to_jsonb(t) = b.j;
SELECT CASE WHEN (SELECT count(*) FROM public.line_conditions) = (SELECT count(*) FROM _lc_before) + 1 THEN 'CHECK_OK total_rows_plus1' ELSE (1 / (count(*) - count(*)))::text END;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK canonical_unique_in_group 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'single' AND canonical = '雑誌付き';
-- CN0025 は不変（K3）。other_rows_unchanged に含まれるが、名指しでも確かめる
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK CN0025_unchanged 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM _lc_before b JOIN public.line_conditions t ON t.id = b.id WHERE t.code = 'CN0025' AND to_jsonb(t) = b.j;
-- products の件数は増えない（K5）
SELECT CASE WHEN count(*) = current_setting('ap.products_before')::bigint THEN 'CHECK_OK products_unchanged ' || count(*) ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products;

:end;
SELECT 'APPLY_END';
