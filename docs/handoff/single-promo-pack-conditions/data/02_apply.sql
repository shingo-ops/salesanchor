-- ADR-1031 S2 適用。本番での実行は Opus（担当は実行しない）。コード反映（PR マージ・デプロイ・migration 適用）の後に流す。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : psql -v end=ROLLBACK -f 02_apply.sql   （全部の件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : psql -v end=COMMIT   -f 02_apply.sql   （DRY-RUN が全部 OK だった後だけ）
-- id は identity に任せる。件数が違えば 1/0 で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;

-- 1. 状態 8 行（single 5・promo_pack 3）。PSA の式: (?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?N(?![0-9０-９])
WITH i AS (
    INSERT INTO public.line_conditions
        (code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, unit_id, note, value_group, value_rank)
    VALUES
    ('CN0015', 'PSA10',    'シングル系',     true, 2,  '(?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?(10|１０)(?![0-9０-９])', '', 'REGEX',   'OUTPUT', NULL, 'シングル系の鑑定品 PSA10（ADR-1031）', 'single', 1),
    ('CN0016', 'PSA9',     'シングル系',     true, 2,  '(?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?(9|９)(?![0-9０-９])',   '', 'REGEX',   'OUTPUT', NULL, 'シングル系の鑑定品 PSA9（ADR-1031）',  'single', 2),
    ('CN0017', 'PSA8',     'シングル系',     true, 2,  '(?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?(8|８)(?![0-9０-９])',   '', 'REGEX',   'OUTPUT', NULL, 'シングル系の鑑定品 PSA8（ADR-1031）',  'single', 3),
    ('CN0018', 'PSA7以下', 'シングル系',     true, 2,  '(?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?[1-7１-７](?![0-9０-９])', '', 'REGEX',   'OUTPUT', NULL, 'シングル系の鑑定品 PSA1〜7（ADR-1031）', 'single', 4),
    ('CN0019', 'Single',   'シングル系',     true, 10, '', '', 'KEYWORD', 'OUTPUT', NULL, 'シングル系で状態語が無いときの状態。配信する。search_kw は空（どの文にも当たらない。コードの R7:単品既定 だけが返す）（ADR-1031）', 'single', 5),
    ('CN0020', '未開封',   'プロモパック系', true, 10, '', '', 'KEYWORD', 'OUTPUT', NULL, 'プロモパック系で状態語が無いときの状態。配信する。search_kw は空（コードの R8:プロモパック既定 だけが返す）（ADR-1031）', 'promo_pack', 1),
    ('CN0021', '開封済み', 'プロモパック系', true, 2,  '(?<!未)開封(?!前|していない|なし|不可)', '', 'REGEX', 'OUTPUT', NULL, 'プロモパック系の開封済み（ADR-1031）', 'promo_pack', 2),
    ('CN0022', 'PSA10',    'プロモパック系', true, 2,  '(?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?(10|１０)(?![0-9０-９])', '', 'REGEX', 'OUTPUT', NULL, 'プロモパック系の鑑定品 PSA10（ADR-1031）', 'promo_pack', 3)
    RETURNING id
)
SELECT CASE WHEN count(*) = 8 THEN 'INSERTED conditions|8' ELSE (1 / (count(*) - count(*)))::text END FROM i;

-- 2. 区分「プロモパック系」（前例: 便SU の PC_SET）
WITH ins AS (
    INSERT INTO public.tcg_product_categories (code, display_name, kubun_type, is_active, tenant_id)
    SELECT 'PC_PROMO_PACK', 'Promo pack', 'プロモパック系', TRUE, NULL
     WHERE NOT EXISTS (SELECT 1 FROM public.tcg_product_categories WHERE code = 'PC_PROMO_PACK')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED category|1' ELSE (1 / (count(*) - count(*)))::text END FROM ins;

-- 3. 3 商品の区分を 2（シングル系）→ プロモパック系へ。WHERE は id と今の区分 2 の両方
WITH upd AS (
    UPDATE public.products
       SET product_category_id = (SELECT id FROM public.tcg_product_categories WHERE code = 'PC_PROMO_PACK')
     WHERE id IN (440525, 466083, 466077) AND product_category_id = 2
    RETURNING id
)
SELECT CASE WHEN count(*) = 3 THEN 'UPDATED products|3' ELSE (1 / (count(*) - count(*)))::text END FROM upd;

-- 4. 適用後の確認（件数が違えば失敗）
SELECT CASE WHEN count(*) = 24 THEN 'CHECK_OK conditions 24' ELSE (1 / (count(*) - count(*)))::text END FROM public.line_conditions;
SELECT CASE WHEN count(*) = 3 THEN 'CHECK_OK products 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE p.id IN (440525, 466083, 466077) AND c.code = 'PC_PROMO_PACK' AND c.kubun_type = 'プロモパック系' AND c.is_active;

:end;
SELECT 'APPLY_END';
