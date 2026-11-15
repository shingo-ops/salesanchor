-- ADR-1012 段階4 便2a の戻し（手動実行のみ・本番デプロイでは実行しない）。便2b を戻した後にだけ流す。
-- 出来事の kind・actor の決まりは戻さない（case_report の行があると狭めると失敗するため。値が 1 つ多く許されるだけで害は無い。前例 migrations/20261113_100001_create_secretary_rules_down.sql）。
BEGIN;
ALTER TABLE ops_case.reports DROP CONSTRAINT IF EXISTS reports_incident_id_kind_key;
ALTER TABLE ops_case.reports DROP CONSTRAINT IF EXISTS reports_kind_check;
ALTER TABLE ops_case.reports DROP COLUMN IF EXISTS kind;
COMMIT;
