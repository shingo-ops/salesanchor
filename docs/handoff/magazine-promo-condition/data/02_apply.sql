-- 状態「雑誌付き」(CN0025) 適用。本番での実行は PO の `!`（担当は実行しない）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : psql -v end=ROLLBACK -f 02_apply.sql   （全部の件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : psql -v end=COMMIT   -f 02_apply.sql   （DRY-RUN が全部 OK だった後だけ）
-- id は identity に任せる。code は固定（CN0025。最大値からの採番はしない）。件数が違えば 1/0 で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;

-- 0. 既存 3 行（群 promo_pack）の適用前の全列を控える（取引の中だけ）
CREATE TEMP TABLE _pp_before ON COMMIT DROP AS
  SELECT id, to_jsonb(t) AS j FROM public.line_conditions t WHERE t.value_group = 'promo_pack';
SELECT CASE WHEN count(*) = 3 THEN 'BEFORE_OK promo_pack 3' ELSE (1 / (count(*) - count(*)))::text END FROM _pp_before;

-- 1. 状態 1 行。単位は Booklet（line_units id 17。副問い合わせで Booklet であることを確かめる）
WITH i AS (
    INSERT INTO public.line_conditions
        (code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, unit_id, note, value_group, value_rank)
    SELECT 'CN0025', '雑誌付き', 'プロモパック系', true, 2, '雑誌[\s　]*(付き|つき)', '', 'REGEX', 'OUTPUT',
           (SELECT id FROM public.line_units WHERE id = 17 AND canonical = 'Booklet'),
           'プロモパック系で雑誌付きと書かれた行の状態。単位は冊（ADR-1023/1031/1035、2026-10-20 PO）',
           'promo_pack', 4
    RETURNING id, canonical, unit_id
)
SELECT CASE WHEN count(*) = 1 AND count(*) FILTER (WHERE canonical = '雑誌付き' AND unit_id = 17) = 1
            THEN 'INSERTED conditions|1' ELSE (1 / (count(*) - count(*)))::text END FROM i;

-- 2. 適用後の確認（件数が違えば失敗）
SELECT CASE WHEN count(*) = 4 THEN 'CHECK_OK promo_pack_rows 4' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'promo_pack';
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK CN0025 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE code = 'CN0025' AND canonical = '雑誌付き' AND app_kubun = 'プロモパック系' AND is_active AND priority = 2
   AND search_kw = '雑誌[\s　]*(付き|つき)' AND exclude_kw = '' AND match_type = 'REGEX' AND effect = 'OUTPUT'
   AND unit_id = 17 AND value_group = 'promo_pack' AND value_rank = 4;
SELECT CASE WHEN count(*) = 3 THEN 'CHECK_OK existing_rows_unchanged 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM _pp_before b JOIN public.line_conditions t ON t.id = b.id WHERE to_jsonb(t) = b.j;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK canonical_unique_in_group 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'promo_pack' AND canonical = '雑誌付き';

:end;
SELECT 'APPLY_END';
