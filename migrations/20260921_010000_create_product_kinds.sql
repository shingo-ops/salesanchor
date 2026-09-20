-- ============================================================================
-- Migration 20260921_010000: public.product_kinds 新設（大分類）
--
-- ADR-156: 商品分類ツリー Phase 1
--   大分類 (product_kinds) → 中分類 (type_master) → 小分類 (product_lines)
--   の3層ツリー構造のうち、大分類テーブルを新設する。
--
-- ADR-155 準拠: seed なし（値の投入は CSV アプリ経由）
-- ADR-025: 本番フェーズ移行後の手動 INSERT 禁止
--
-- 冪等性: CREATE TABLE IF NOT EXISTS / DROP TRIGGER IF EXISTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.product_kinds (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    name_en       VARCHAR(100),
    display_order INTEGER      NOT NULL DEFAULT 100,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_kinds_sort ON public.product_kinds (display_order, id);

-- updated_at 自動更新トリガ（product_lines の set_updated_at_product_lines と同パターン）
CREATE OR REPLACE FUNCTION public.set_updated_at_product_kinds()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_product_kinds_updated_at ON public.product_kinds;
CREATE TRIGGER trg_product_kinds_updated_at
    BEFORE UPDATE ON public.product_kinds
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_product_kinds();

COMMENT ON TABLE public.product_kinds IS
    '大分類マスタ（ADR-156）。TCG / 書籍 / ゲーム機 など最上位の商品種別。UI から増減可能。';

-- ============================================================================
-- Rollback:
--   DROP TRIGGER IF EXISTS trg_product_kinds_updated_at ON public.product_kinds;
--   DROP FUNCTION IF EXISTS public.set_updated_at_product_kinds();
--   DROP TABLE IF EXISTS public.product_kinds;
-- ============================================================================
