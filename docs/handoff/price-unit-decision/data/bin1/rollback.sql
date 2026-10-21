-- 価格で単位を決める 便1 設定の戻し: 戻すときだけ。30→7 と元の note（便BB の commit.sql）に戻す。
\set ON_ERROR_STOP on
BEGIN;
WITH upd AS (
    UPDATE public.tcg_distribution_settings
       SET value = '7', note = '買取価格による単位・状態の判定: 買取の行が最後に見えてからの日数の上限'
     WHERE key = 'unit_buyback_max_age_days' AND value = '30'
    RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'REVERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
COMMIT;
SELECT 'ROLLBACK_DONE';
