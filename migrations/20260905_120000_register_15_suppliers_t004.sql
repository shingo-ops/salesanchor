-- Migration: 20260905_120000_register_15_suppliers_t004
-- 目的: 仕入元マスタ 15件 (SP0188〜SP0202) を tenant_004 に登録し、
--       LINE チャンネル行 (channel='line', external_id=NULL) も同時作成する
--
-- 冪等性: ON CONFLICT (code) DO NOTHING / ON CONFLICT (channel, external_id) DO NOTHING
-- ※ PostgreSQL は NULL 同士を UNIQUE 重複と見なさないため、
--   external_id=NULL の supplier_channels 行は各仕入元に個別挿入可能
--
-- 禁止: 既存 tcg_suppliers 行の UPDATE/DELETE は行わない

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
    RAISE NOTICE '20260905_120000: no-op (values deprecated per ADR-155)';

END $$;
