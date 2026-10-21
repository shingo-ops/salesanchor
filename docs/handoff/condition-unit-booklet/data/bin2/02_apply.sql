-- ADR-1035 便2 適用。本番での実行は Opus（担当は実行しない）。コード反映（PR マージ・デプロイ・migration 適用）の後に流す。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : psql -v end=ROLLBACK -f 02_apply.sql   （全部の件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : psql -v end=COMMIT   -f 02_apply.sql   （DRY-RUN が全部 OK だった後だけ）
-- id は identity に任せる。code は固定（CN0023=With booklet・CN0024=Without booklet。最大値からの採番はしない）。件数が違えば 1/0 で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;

-- 1. 状態 2 行（booklet 群）。単位は With booklet のみ Booklet（line_units id 17）、Without booklet は空
WITH i AS (
    INSERT INTO public.line_conditions
        (code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, unit_id, note, value_group, value_rank)
    SELECT v.code, v.canonical, 'ブックレット系', true, v.priority, v.search_kw, '', v.match_type, 'OUTPUT', v.unit_id, v.note, 'booklet', v.value_rank
      FROM (VALUES
        ('CN0023', 'With booklet', 10, '', 'KEYWORD',
         (SELECT id FROM public.line_units WHERE id = 17 AND canonical = 'Booklet'), 1,
         'ブックレット系で状態語が無いときの状態。配信する。search_kw は空（どの文にも当たらない。コードの R9:ブックレット既定 だけが返す）（ADR-1035）'),
        ('CN0024', 'Without booklet', 2,
         '(?i)((ブックレット|冊子)[\s　]*(無し|なし|抜き|欠品|欠け)|(?<![a-z])(no|without)[\s　]+booklet)', 'REGEX',
         NULL::int, 2,
         'ブックレット系の冊子無し。単位は空（冊子が付いていない品物を冊で数えない。原文の単位語があればそれを使う）（ADR-1035）')
      ) AS v(code, canonical, priority, search_kw, match_type, unit_id, value_rank, note)
    RETURNING id, canonical, unit_id
)
SELECT CASE WHEN count(*) = 2 AND count(*) FILTER (WHERE canonical = 'With booklet' AND unit_id = 17) = 1
            THEN 'INSERTED conditions|2' ELSE (1 / (count(*) - count(*)))::text END FROM i;

-- 2. 区分「ブックレット系」（前例: ADR-1031 の PC_PROMO_PACK）
WITH ins AS (
    INSERT INTO public.tcg_product_categories (code, display_name, kubun_type, is_active, tenant_id)
    SELECT 'PC_BOOKLET', 'Booklet', 'ブックレット系', TRUE, NULL
     WHERE NOT EXISTS (SELECT 1 FROM public.tcg_product_categories WHERE code = 'PC_BOOKLET')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED category|1' ELSE (1 / (count(*) - count(*)))::text END FROM ins;

-- 3. 商品 440415 の区分を 2（シングル系）→ ブックレット系へ。WHERE は id と今の区分 2 の両方
WITH upd AS (
    UPDATE public.products
       SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_BOOKLET')
     WHERE id = 440415 AND product_category_id = 2
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED products|1' ELSE (1 / (count(*) - count(*)))::text END FROM upd;

-- 4. 適用後の確認（件数が違えば失敗）
SELECT CASE WHEN count(*) = 2 THEN 'CHECK_OK booklet_conditions 2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group = 'booklet' AND app_kubun = 'ブックレット系' AND is_active AND effect = 'OUTPUT';
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK product 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id = 440415 AND c.code = 'PC_BOOKLET' AND c.kubun_type = 'ブックレット系' AND c.is_active;

:end;
SELECT 'APPLY_END';
