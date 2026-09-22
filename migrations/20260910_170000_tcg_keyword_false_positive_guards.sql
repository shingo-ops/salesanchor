-- CARD-LINE-KEYWORD-GUARDS-01: tenant_004 only; validate all before mutation.
--
-- NEUTRALIZED (ADR-155, 2026-09-18):
-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- 元の内容は git history で参照可能。
--

DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: false positive guard keywords removed — manage via app/CSV'; END $$;
