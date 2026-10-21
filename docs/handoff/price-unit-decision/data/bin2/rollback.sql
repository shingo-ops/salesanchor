-- 価格で単位を決める 便2 設定の戻し: 戻すときだけ。ADR-1036。
-- PO 承認 2026-10-21『1』: ファイルとして置くだけ。実行は PO が ! で行う。
-- commit.sql の逆: public.tcg_distribution_settings の key='unit_buyback_pack_max'（0.2）の 1 行を消す。
-- 順序: 先にコード（unit_buyback_pack_max を読む便2）を revert してからこれを流す。
-- 消えた件数がちょうど 1 でなければゼロ除算で失敗し、ROLLBACK に進む（COMMIT に進まない）。
\set ON_ERROR_STOP on
BEGIN;
WITH del AS (
    DELETE FROM public.tcg_distribution_settings
     WHERE key = 'unit_buyback_pack_max'
    RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'DELETED|1' ELSE (1 / (count(*) - count(*)))::text END FROM del;
SELECT CASE WHEN count(*) = 0 THEN 'CHECK_OK pack_max gone' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_pack_max';
COMMIT;
SELECT 'ROLLBACK_DONE';
