-- 便UP 設定2key投入 commit: dryrun 成功の後だけ。ADR-1007（値は data SQL で1回だけ投入）。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.tcg_distribution_settings (key, value, note) VALUES
        ('unit_price_check_ratio', '3', '単位と価格の確認: 相場とのずれの倍率の上限（これを超え、別の単位の相場の方が近いと要確認）'),
        ('unit_price_check_min_posts', '3', '単位と価格の確認: 相場に使う別々の投稿の数の最小')
    RETURNING key
)
SELECT CASE WHEN count(*) = 2 THEN 'INSERTED|2' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 2 THEN 'CHECK_OK 2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE (key, value) IN (('unit_price_check_ratio', '3'), ('unit_price_check_min_posts', '3'));
COMMIT;
SELECT 'COMMIT_DONE';
