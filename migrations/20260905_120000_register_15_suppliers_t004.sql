-- Migration: 20260905_120000_register_15_suppliers_t004
-- 目的: 仕入元マスタ 15件 (SP0188〜SP0202) を tenant_004 に登録し、
--       LINE チャンネル行 (channel='line', external_id=NULL) も同時作成する
--
-- 冪等性: ON CONFLICT (code) DO NOTHING / ON CONFLICT (channel, external_id) DO NOTHING
-- ※ PostgreSQL は NULL 同士を UNIQUE 重複と見なさないため、
--   external_id=NULL の supplier_channels 行は各仕入元に個別挿入可能
--
-- 禁止: 既存 tcg_suppliers 行の UPDATE/DELETE は行わない

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): tenant_004 の仕入れ先15件と LINE の連絡手段の行の登録（INSERT 2つ）を外した。
-- 一度きりの登録は終わっている。毎回の本番反映で、消した仕入れ先の行が tenant_004.tcg_suppliers に戻っていた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #24
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: tenant_004 supplier registration removed (20260905_120000)'; END $$;
