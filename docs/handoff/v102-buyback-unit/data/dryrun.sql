-- 便BB 設定4key投入 dryrun: 入れて検査して必ず ROLLBACK。件数が4でなければゼロ除算で失敗する。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.tcg_distribution_settings (key, value, note) VALUES
        ('unit_buyback_box_min', '0.5', '買取価格による単位・状態の判定: 価格÷買取相場がこの値以上、box_max 未満なら Sealed box'),
        ('unit_buyback_box_max', '2', '買取価格による単位・状態の判定: 箱とみなす比の上限（これ未満）'),
        ('unit_buyback_case_min', '6', '買取価格による単位・状態の判定: 価格÷買取相場がこの値以上なら Case'),
        ('unit_buyback_max_age_days', '7', '買取価格による単位・状態の判定: 買取の行が最後に見えてからの日数の上限')
    RETURNING key
)
SELECT CASE WHEN count(*) = 4 THEN 'INSERTED|4' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 4 THEN 'CHECK_OK 4' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings
 WHERE (key, value) IN (('unit_buyback_box_min', '0.5'), ('unit_buyback_box_max', '2'), ('unit_buyback_case_min', '6'), ('unit_buyback_max_age_days', '7'));
ROLLBACK;
SELECT 'DRYRUN_OK';
