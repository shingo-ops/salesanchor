-- ============================================================================
-- Migration 20260620_010000: inventory aggregation rules
--
-- PR-1:
--   価格許容差 / 在庫差 の正本ルールを public に tenant-independent で保持する。
--   既存テーブルは変更せず、追加のみ。
--
-- Seed values (ver4.1):
--   Case                 1000 / 5
--   Sealed box            100 / 30
--   Damaged sealed box     100 / 10
--   No shrink box         100 / 5
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.inventory_aggregation_rules (
    id BIGSERIAL PRIMARY KEY,
    condition TEXT NOT NULL,
    price_tolerance INTEGER NOT NULL CHECK (price_tolerance >= 0),
    stock_tolerance INTEGER NOT NULL CHECK (stock_tolerance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT inventory_aggregation_rules_condition_key UNIQUE (condition)
);

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- 集計ルール 4 行の seed と上書きを外した。値は本番に入っている（ver4.1）。
-- 新規環境の既定は backend/app/services/inventory_aggregation.py の DEFAULT_AGGREGATION_RULES、
-- 試験の seed は backend/tests/seed_data.py。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: inventory_aggregation_rules seed removed'; END $$;
