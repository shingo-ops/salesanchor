-- 便UP 設定3key投入 dryrun: 入れて検査して必ず ROLLBACK。件数が3でなければゼロ除算で失敗する。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.tcg_distribution_settings (key, value, note) VALUES
        ('unit_price_check_ratio', '3', '単位と価格の確認: 相場とのずれの倍率の上限（これを超え、別の単位の相場の方が近いと要確認）'),
        ('unit_price_check_min_posts', '3', '単位と価格の確認: 相場に使う別々の投稿の数の最小'),
        ('unit_price_check_single_ratio', '5', '単位と価格の確認: 比べる別単位の相場が無いとき、価格が相場のこの倍率以上（高い側だけ）なら要確認')
    RETURNING key
)
SELECT CASE WHEN count(*) = 3 THEN 'INSERTED|3' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 3 THEN 'CHECK_OK 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings
 WHERE (key, value) IN (('unit_price_check_ratio', '3'), ('unit_price_check_min_posts', '3'), ('unit_price_check_single_ratio', '5'));
ROLLBACK;
SELECT 'DRYRUN_OK';
