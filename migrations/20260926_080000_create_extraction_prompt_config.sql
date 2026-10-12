-- ============================================================================
-- Migration 20260926_080000: public.extraction_prompt_config 新設
--
-- Gemini 抽出プロンプトをDB管理化し、管理画面から編集可能にする。
-- prompt_key で種別を区別する（'base_extraction' / 'work_id_extraction'）。
--   - システム全体で共通（supplier別ではない）
--   - public スキーマ（tenant_id を持たない）
--
-- 冪等: CREATE TABLE / INDEX IF NOT EXISTS。
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.extraction_prompt_config (
    id          SERIAL PRIMARY KEY,
    prompt_key  VARCHAR(100) NOT NULL UNIQUE,
    prompt_text TEXT NOT NULL DEFAULT '',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    version     INTEGER NOT NULL DEFAULT 1,
    updated_by  INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extraction_prompt_config_key
    ON public.extraction_prompt_config (prompt_key);

-- updated_at 自動更新トリガー（supplier_prompts パターン踏襲）
CREATE OR REPLACE FUNCTION public.set_updated_at_extraction_prompt_config()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_updated_at_extraction_prompt_config ON public.extraction_prompt_config;
CREATE TRIGGER trigger_set_updated_at_extraction_prompt_config
    BEFORE UPDATE ON public.extraction_prompt_config
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_extraction_prompt_config();

COMMENT ON TABLE public.extraction_prompt_config IS
    'システム全体の Gemini 抽出プロンプト設定。prompt_key で種別を区別する。';

-- ============================================================================
-- Rollback:
--   DROP TRIGGER IF EXISTS trigger_set_updated_at_extraction_prompt_config ON public.extraction_prompt_config;
--   DROP FUNCTION IF EXISTS public.set_updated_at_extraction_prompt_config();
--   DROP TABLE IF EXISTS public.extraction_prompt_config;
-- ============================================================================
