-- 価格で単位を決める 便2 設定 commit: dryrun 成功の後・コード反映の後だけ。ADR-1007。unit_buyback_pack_max=0.2 の 1 行を足す。件数が 1 でなければゼロ除算で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.tcg_distribution_settings (key, value, note) VALUES
        ('unit_buyback_pack_max', '0.2', '買取価格による単位・状態の判定: 比がこの値以下ならパック')
    RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 0.2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_pack_max' AND value = '0.2' AND note = '買取価格による単位・状態の判定: 比がこの値以下ならパック';
COMMIT;
SELECT 'COMMIT_DONE';
