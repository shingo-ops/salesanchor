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

INSERT INTO public.inventory_aggregation_rules
    (condition, price_tolerance, stock_tolerance)
VALUES
    ('Case', 1000, 5),
    ('Sealed box', 100, 30),
    ('Damaged sealed box', 100, 10),
    ('No shrink box', 100, 5)
ON CONFLICT (condition) DO UPDATE SET
    price_tolerance = EXCLUDED.price_tolerance,
    stock_tolerance = EXCLUDED.stock_tolerance,
    updated_at = NOW();
