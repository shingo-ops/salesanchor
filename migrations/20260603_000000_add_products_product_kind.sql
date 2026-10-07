-- ============================================================================
-- Migration 20260603_000000: ADR-093 — public.products に「商品種類」(product_kind)
--   を additive 追加。
--
-- 商品種類 = 最上位のジャンル区分。現状の値は 'TCG' のみ（将来 'フィギュア' 等の
-- 他ジャンルが増えた時に対応するための器）。既存商品はすべて TCG 前提で運用してきた
-- ため 'TCG' でバックフィルする。
--
-- 階層: 商品種類(product_kind='TCG') > 種別(tcg_type='ポケモンカード') > シリーズ。
--
-- 適用対象: public スキーマ (1 回のみ)
-- 冪等: ADD COLUMN IF NOT EXISTS で再走可。DEFAULT 'TCG' で既存行も自動補完。
-- additive-only (backend/CLAUDE.md): 列追加のみ。削除・型変更なし。
-- ============================================================================

ALTER TABLE public.products
    ADD COLUMN IF NOT EXISTS product_kind VARCHAR(50) DEFAULT 'TCG';

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- product_kind の補完 UPDATE を外した（本番は 0 行）。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: product_kind backfill removed'; END $$;
