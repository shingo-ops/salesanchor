-- Migration: public.inventory に source_kind カラムを追加
--
-- 目的 (ADR SA-05):
--   public.inventory が B_feed 専用であることを構造上明示する。
--   A在庫は tenant_{NNN}.own_inventory を参照すること（own_inventory PR#6 完了後に適用）。
--
-- ⚠️  前提条件: PR#6 (20260604_140000_create_own_inventory.sql) 適用済みであること。
--     public.inventory に A行が存在しないことは E確認済み（supplier_id NOT NULL 構造上不可）。
--
-- 影響テーブル: public.inventory
-- 冪等: ADD COLUMN IF NOT EXISTS

ALTER TABLE public.inventory
    ADD COLUMN IF NOT EXISTS source_kind VARCHAR(10) NOT NULL DEFAULT 'B_feed'
    CHECK (source_kind IN ('B_feed'));

COMMENT ON COLUMN public.inventory.source_kind IS
    'B_feed のみ許可。A在庫は tenant_{NNN}.own_inventory を参照のこと（ADR-SA-05/PR#6）';
