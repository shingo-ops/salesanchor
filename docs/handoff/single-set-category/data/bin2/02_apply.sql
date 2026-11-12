-- ADR-1031 What 6 便2 適用。区分「シングルセット系」1 行を足す（記録 SQL。migration には書かない＝ADR-1007）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : -v end=ROLLBACK   （件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : -v end=COMMIT     （DRY-RUN が全部 OK だった後だけ）
-- id は identity に任せる。件数が違えば 1/0 で失敗し、COMMIT に進まない。前例: ADR-1035 便2 の PC_BOOKLET。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;
SET LOCAL lock_timeout = '1s';

-- 1. 区分「シングルセット系」（共用＝tenant_id NULL）
WITH ins AS (
    INSERT INTO public.tcg_product_categories (code, display_name, kubun_type, is_active, tenant_id)
    SELECT 'PC_SINGLE_SET', 'Single set', 'シングルセット系', TRUE, NULL
     WHERE NOT EXISTS (SELECT 1 FROM public.tcg_product_categories
                        WHERE code = 'PC_SINGLE_SET' OR kubun_type = 'シングルセット系')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED category|1' ELSE (1 / (count(*) - count(*)))::text END FROM ins;

-- 2. 適用後の確認（件数が違えば失敗）
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK category 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories
 WHERE code = 'PC_SINGLE_SET' AND display_name = 'Single set' AND kubun_type = 'シングルセット系' AND is_active AND tenant_id IS NULL;
SELECT CASE WHEN count(*) = 7 THEN 'CHECK_OK categories_total 7' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_product_categories;
SELECT CASE WHEN count(*) = 0 THEN 'CHECK_OK single_set_products 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.products p JOIN public.tcg_product_categories c ON c.id = p.product_category_id
 WHERE c.kubun_type = 'シングルセット系';

:end;
SELECT 'APPLY_END';
