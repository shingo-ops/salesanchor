-- ADR-1077 便1 の戻し（手動実行のみ・本番デプロイでは実行しない）。2 表と方針・索引を消す。
-- 使いみちの CHECK は戻さない（便2 の後に secretary_regression の行があると、狭めると失敗するため。値が 1 つ多く許されるだけで害は無い）。
BEGIN;
DROP TABLE IF EXISTS public.secretary_rule_checks;
DROP TABLE IF EXISTS public.secretary_rules;
COMMIT;
