-- ONE PIECE magazine 付録プロモ 5商品の整備（tenant_004 専用・冪等）
--
-- 目的: Vol.21 の MULTI 11行と ST21-014 の NONE 1行を解決する（計12行）
-- 承認: Shingo 2026-09-04
-- バックアップ:
--   tenant_004.tcg_products_bak_20260904              (268)
--   tenant_004.product_search_keywords_bak_20260904   (593)
--   tenant_004.product_exclude_keywords_bak_20260904  (128)
--
-- 設計判断:
--   - 既存キーワードは1本も削除しない（追加のみ）
--   - 検証は担当範囲（PM0269〜PM0271）だけを数える。テーブル全体を数えない
--   - 冪等: ON CONFLICT DO NOTHING
--
-- NEUTRALIZED (ADR-155, 2026-09-18):
-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- 元の内容は git history で参照可能。
--

DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: magazine promo product+keyword seed removed — manage via app/CSV'; END $$;
