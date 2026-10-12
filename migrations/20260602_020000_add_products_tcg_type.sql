-- Migration 20260602_020000: ADR-090 PR5a — public.products に tcg_type 列追加 + category から backfill
--
-- 在庫表の「タイプ」を自由文 category（"Pokemon" / "GUNDUM" 等）から TCG 種別マスタ
-- (public.tcg_type_master.code) に統一する。tcg_type 列を追加し、確定済みマッピングで backfill。
-- 冪等: ADD COLUMN IF NOT EXISTS + UPDATE は tcg_type IS NULL のみ対象（再走で上書きしない）。

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_type VARCHAR(50);

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- category から tcg_type を埋める UPDATE 7 本を外した（本番は 0 行）。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: tcg_type backfill removed'; END $$;

CREATE INDEX IF NOT EXISTS idx_public_products_tcg_type ON public.products (tcg_type);
