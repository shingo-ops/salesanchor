-- ============================================================================
-- Migration 20260921_040000: public.condition_definitions テーブル新設
--
-- ADR-156: 商品分類ツリー Phase 1
--   コンディション定義マスタ。product_lines（小分類）ごとに
--   コンディション（状態）の定義を保持し、解析マスタ (conditions) の
--   正規化参照元となる。
--
-- ADR-155 準拠: seed なし（値の投入は CSV アプリ経由）
-- ADR-025: 本番フェーズ移行後の手動 INSERT 禁止
--
-- 冪等性: CREATE TABLE IF NOT EXISTS / DROP TRIGGER IF EXISTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.condition_definitions (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL,
    name          VARCHAR(100) NOT NULL,
    name_en       VARCHAR(100),
    line_id       INTEGER      REFERENCES public.product_lines(id) ON DELETE SET NULL,
    display_order INTEGER      NOT NULL DEFAULT 100,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (code, line_id)
);

CREATE INDEX IF NOT EXISTS idx_condition_definitions_line_id ON public.condition_definitions (line_id);

-- updated_at 自動更新トリガ（product_lines と同パターン）
CREATE OR REPLACE FUNCTION public.set_updated_at_condition_definitions()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_condition_definitions_updated_at ON public.condition_definitions;
CREATE TRIGGER trg_condition_definitions_updated_at
    BEFORE UPDATE ON public.condition_definitions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_condition_definitions();

COMMENT ON TABLE public.condition_definitions IS 'コンディション定義マスタ（ADR-156）。product_lines（小分類）ごとのコンディション定義。解析マスタ（condition 解析テーブル）の正規化参照元。';

-- ============================================================================
-- Rollback:
--   DROP TRIGGER IF EXISTS trg_condition_definitions_updated_at ON public.condition_definitions;
--   DROP FUNCTION IF EXISTS public.set_updated_at_condition_definitions();
--   DROP TABLE IF EXISTS public.condition_definitions;
-- ============================================================================
