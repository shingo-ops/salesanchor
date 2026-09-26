-- ============================================================================
-- Migration 20260603_030000: ドラゴンボール フュージョンワールド 商品マスタ投入
--
-- 公式サイト (dbs-cardgame.com/fw/jp/products) の Booster Pack / Starter Deck を
-- 中央カタログ public.products に投入する（ADR-090: tenant_id=NULL）。
--
-- 冪等: product_code（'DB-<型番>'）の partial UNIQUE で ON CONFLICT DO UPDATE。
--       再実行・本番再適用しても重複せず、値が更新される。
-- category='Dragon Ball' / tcg_type='dragon_ball'（既存規約・migration 085/20260602_020000）。
-- 在庫数は中央カタログのため 0（在庫は仕入元オファーで管理）。
-- additive-only（INSERT のみ）。
-- ============================================================================
--
-- NEUTRALIZED (ADR-155, 2026-09-18):
-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- 元の内容は git history で参照可能。
--

DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: Dragon Ball product seed removed — manage via app/CSV'; END $$;
