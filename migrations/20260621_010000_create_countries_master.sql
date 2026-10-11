-- Foundation F1: public.countries 国台帳（全テナント共有・追加のみ）
-- SSOT: frontend/src/constants/countries.ts
-- 目的: ISO alpha-2 国コード一覧を共有マスタとして提供し、後続 PR で
--       lead.country / company.country_code の統制・backfill に繋ぐ。

CREATE TABLE IF NOT EXISTS public.countries (
    code CHAR(2) PRIMARY KEY,
    name TEXT NOT NULL,
    dial_code TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_countries_active_name
    ON public.countries (is_active, name, code);

CREATE OR REPLACE FUNCTION public.set_updated_at_countries()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_updated_at_countries ON public.countries;
CREATE TRIGGER trigger_set_updated_at_countries
    BEFORE UPDATE ON public.countries
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_countries();

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- 国 190 行の seed と上書きを外した。国の正本は frontend/src/constants/countries.ts、
-- 試験の seed は backend/tests/seed_data.py。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: countries seed removed'; END $$;

COMMENT ON TABLE public.countries IS '国マスタ（ISO 3166-1 alpha-2 / 全テナント共有）';
