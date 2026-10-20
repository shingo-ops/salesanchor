-- 価格で単位を決める 便1 設定の dryrun: 7→30 に更新して検査し、必ず ROLLBACK。行が 1 行でなければゼロ除算で失敗する。ADR-1036。
\set ON_ERROR_STOP on
BEGIN;
WITH upd AS (
    UPDATE public.tcg_distribution_settings
       SET value = '30', note = '買取価格による単位・状態の判定: 行の投稿日時より前の、この日数以内の買取の値だけを使う'
     WHERE key = 'unit_buyback_max_age_days' AND value = '7'
    RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED|1' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 30' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_max_age_days' AND value = '30' AND note = '買取価格による単位・状態の判定: 行の投稿日時より前の、この日数以内の買取の値だけを使う';
ROLLBACK;
SELECT 'DRYRUN_OK';
