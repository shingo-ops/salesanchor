-- ADR-1041 便1 設定 v102_kubun_allowed_units 投入 commit: precheck が CAN_PROCEED|1 で dryrun 成功の後だけ。ADR-1007（値は data SQL で投入）。件数が1でなければゼロ除算で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
BEGIN;
WITH up AS (
    INSERT INTO public.tcg_distribution_settings (key, value, note) VALUES
        ('v102_kubun_allowed_units', '{"箱系": ["Box", "Case", "Pack", "MasterCarton"], "プロモパック系": ["Booklet", "Pack"], "ブックレット系": ["Booklet"]}', '区分ごとに取れる単位の表（ADR-1041）: JSON（区分名 → 単位名の配列）。{} は取り消し（表なし）。コードの検査に通らない値は使われない')
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'UPSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM up;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings
 WHERE key = 'v102_kubun_allowed_units'
   AND value = '{"箱系": ["Box", "Case", "Pack", "MasterCarton"], "プロモパック系": ["Booklet", "Pack"], "ブックレット系": ["Booklet"]}';
COMMIT;
SELECT 'COMMIT_DONE';
