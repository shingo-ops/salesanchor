-- ============================================================================
-- Migration 086: public.tcg_type_master へ TCG 種別を追加 (ADR-083 拡張 / QA 2026-05-31)
--
-- スプレッドシートの各 TCG (GUNDUM / Weiss Schwarz / Degimon / hololive /
-- LORCANA / Xross Stars) を種別として追加する。データ(シリーズ)の有無に関わらず
-- 種別だけは登録する要望に対応。既存の one_piece/dragon_ball/union_arena/yugioh は
-- migration 085 で登録済み。
--
-- 冪等: ON CONFLICT (code) DO NOTHING。
-- ============================================================================
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- 種別 6 行（gundam ... xross_stars）の seed を外した。type_master は画面（ADR-156）で管理する。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: type master additional seed removed (086)'; END $$;

-- ============================================================================
-- Rollback:
--   DELETE FROM public.tcg_type_master
--     WHERE code IN ('gundam','weiss_schwarz','digimon','hololive','lorcana','xross_stars');
-- ============================================================================
