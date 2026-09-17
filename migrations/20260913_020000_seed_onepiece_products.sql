-- ============================================================================
-- Migration 20260913_020000: ONE PIECE カードゲーム商品マスタ 168 件を中央カタログへ投入
--
-- ADR-090: public 中央カタログ（tenant_id=NULL）。在庫数は 0。
-- Dragon Ball v2 seed (20260913_010000) と同一形式。
-- 冪等: ON CONFLICT(product_code) WHERE product_code IS NOT NULL DO UPDATE。
-- ============================================================================
--
-- NEUTRALIZED (ADR-155, 2026-09-18):
-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- 元の内容は git history で参照可能。
--

DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: ONE PIECE product seed removed — manage via app/CSV'; END $$;
