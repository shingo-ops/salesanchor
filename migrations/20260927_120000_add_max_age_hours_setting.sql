-- max_age_hours setting for distribution time filter
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- max_age_hours の seed を外した。アプリは未設定のとき既定値を使う（tcg_distribution_svc.py）。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: max_age_hours seed removed'; END $$;
