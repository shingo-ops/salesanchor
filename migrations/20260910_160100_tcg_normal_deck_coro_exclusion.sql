-- CARD-LINE-WORK-MATCHING-V3-01: preserve existing words; never register a product.
--
-- NEUTRALIZED (ADR-155, 2026-09-18):
-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- 元の内容は git history で参照可能。
--

DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: coro exclusion keyword removed — manage via app/CSV'; END $$;
